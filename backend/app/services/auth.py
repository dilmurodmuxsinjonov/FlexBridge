"""Authentication, Real Argon2id, Base32/Hex TOTP, Persistent SQL Sessions & Immediate Revocation (FIX-03, FIX-04).

Fixes:
- R-01: Blocks privileged role self-assignment on public `/api/v1/auth/register`; provides server-side `ActorContext`.
- R-03: Persists users and sessions in SQLAlchemy database (`app.db.storage`) so sessions are shared across worker processes and survive restarts.
- R-12: Uses real `argon2-cffi` RFC 9106 Argon2id (`Type.ID`) instead of PBKDF2.
- INV-15: Checks primary SQL session/user revocation on every validation alongside L1 cache eviction.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from argon2.low_level import Type, hash_secret_raw
from sqlalchemy import select

from app.core.audit import AppendOnlyAuditStore
from app.core.config import settings
from app.db.storage import get_engine, sessions_table, users_table

PRIVILEGED_ROLES_FORBIDDEN_ON_PUBLIC_REGISTER = frozenset(
    {
        "SUPER_ADMIN",
        "ADMIN",
        "PLATFORM_ADMIN",
        "FINANCE_ADMIN",
        "FINANCE",
        "MODERATOR",
        "SUPPORT_AGENT",
        "AUDITOR",
        "INST_ADMIN",
        "INST_INTERNSHIP_COORDINATOR",
        "ACADEMIC_SUPERVISOR",
    }
)


class AuthError(Exception):
    """Raised on authentication, session, scope, or revocation errors."""

    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _normalize_salt_bytes(salt: str | None) -> tuple[str, bytes]:
    salt_label = secrets.token_hex(8) if salt is None else salt
    raw = salt_label.encode("utf-8")
    if len(raw) < 8:
        raw = raw.ljust(8, b"0")
    return salt_label, raw


def hash_password(password: str, salt: str | None = None) -> str:
    """Compute a genuine RFC 9106 Argon2id password hash using `argon2-cffi` (`FIX-03`, `R-12`)."""
    salt_label, salt_bytes = _normalize_salt_bytes(salt)
    dk = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt_bytes,
        time_cost=2,
        memory_cost=19456,
        parallelism=1,
        hash_len=32,
        type=Type.ID,
    )
    return f"$argon2id$v=19$m=19456,t=2,p=1${salt_label}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored Argon2id hash in constant time."""
    if not stored_hash.startswith("$argon2id$"):
        return False
    parts = stored_hash.split("$")
    if len(parts) != 6:
        return False
    salt_label = parts[4]
    expected = hash_password(password, salt=salt_label)
    return hmac.compare_digest(expected, stored_hash)


def _decode_totp_secret(secret_str: str) -> bytes:
    cleaned = secret_str.strip().replace(" ", "")
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        padded = cleaned.upper() + "=" * ((8 - len(cleaned) % 8) % 8)
        return base64.b32decode(padded, casefold=True)


def generate_totp_code(secret_str: str, timestamp: int | None = None, step: int = 30) -> str:
    """Generate a 6-digit RFC 6238 TOTP code for hex or base32 `secret_str`."""
    ts = int(time.time()) if timestamp is None else timestamp
    counter = ts // step
    key = _decode_totp_secret(secret_str)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code_int:06d}"


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class AuthSessionService:
    """Manages `users` (`DB-001`) and `sessions` (`DB-004`) backed by persistent SQL + L1 cache (`INV-15`)."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    _l1_permission_cache: dict[str, tuple[float, dict[str, Any]]] = field(default_factory=dict)
    _revoked_sessions: set[str] = field(default_factory=set)

    def _persist_user(self, user: dict[str, Any]) -> None:
        engine = get_engine()
        with engine.begin() as conn:
            existing = conn.execute(select(users_table.c.id).where(users_table.c.id == user["id"])).first()
            values = {
                "id": user["id"],
                "display_name": user["display_name"],
                "password_hash": user["password_hash"],
                "status": user["status"],
                "adult_declared_at": user["adult_declared_at"],
                "roles_json": json.dumps(user["roles"]),
                "totp_enabled": 1 if user.get("totp_secret") else 0,
                "totp_secret": user.get("totp_secret"),
                "created_at": user["created_at"],
            }
            if existing:
                conn.execute(users_table.update().where(users_table.c.id == user["id"]).values(**values))
            else:
                conn.execute(users_table.insert().values(**values))
        self.users[user["id"]] = dict(user)

    def _load_user(self, user_id: str) -> dict[str, Any] | None:
        engine = get_engine()
        with engine.connect() as conn:
            row = conn.execute(select(users_table).where(users_table.c.id == user_id)).mappings().first()
            if row is not None:
                user = {
                    "id": row["id"],
                    "display_name": row["display_name"],
                    "password_hash": row["password_hash"],
                    "status": row["status"],
                    "adult_declared_at": row["adult_declared_at"],
                    "roles": json.loads(row["roles_json"]),
                    "totp_secret": row["totp_secret"],
                    "created_at": row["created_at"],
                }
                self.users[user_id] = user
                return dict(user)
        return self.users.get(user_id)

    def _persist_session(self, session: dict[str, Any]) -> None:
        engine = get_engine()
        with engine.begin() as conn:
            existing = conn.execute(
                select(sessions_table.c.session_id).where(sessions_table.c.session_id == session["session_id"])
            ).first()
            values = {
                "session_id": session["session_id"],
                "token_digest": session["token_digest"],
                "user_id": session["user_id"],
                "status": session["status"],
                "roles_json": json.dumps(session["roles"]),
                "created_at": session["created_at"],
                "expires_at": session["expires_at"],
                "revoked_at": session.get("revoked_at"),
                "revoked_by": session.get("revoked_by"),
                "revoke_reason": session.get("revoke_reason"),
            }
            if existing:
                conn.execute(
                    sessions_table.update()
                    .where(sessions_table.c.session_id == session["session_id"])
                    .values(**values)
                )
            else:
                conn.execute(sessions_table.insert().values(**values))
        self.sessions[session["session_id"]] = dict(session)

    def _load_session(self, session_id: str) -> dict[str, Any] | None:
        engine = get_engine()
        with engine.connect() as conn:
            row = (
                conn.execute(select(sessions_table).where(sessions_table.c.session_id == session_id))
                .mappings()
                .first()
            )
            if row is not None:
                session = {
                    "session_id": row["session_id"],
                    "token_digest": row["token_digest"],
                    "user_id": row["user_id"],
                    "status": row["status"],
                    "roles": json.loads(row["roles_json"]),
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                    "revoked_at": row["revoked_at"],
                    "revoked_by": row["revoked_by"],
                    "revoke_reason": row["revoke_reason"],
                }
                self.sessions[session_id] = session
                return dict(session)
        return self.sessions.get(session_id)

    def register_user(
        self,
        *,
        display_name: str,
        password: str,
        adult_confirmed: bool,
        roles: list[str] | None = None,
        enable_totp: bool = False,
        allow_privileged_roles: bool = False,
    ) -> dict[str, Any]:
        """Register an 18+ user account (`DB-001 users`), blocking privileged self-registration (`R-01`)."""
        if not adult_confirmed:
            raise AuthError(
                code="ADULT_DECLARATION_REQUIRED",
                message="FlexBridge R1 faqat 18+ foydalanuvchilar uchun mo'ljallangan",
                status_code=422,
            )

        requested_roles = list(roles or ["CANDIDATE"])
        if not allow_privileged_roles:
            forbidden = [r for r in requested_roles if r in PRIVILEGED_ROLES_FORBIDDEN_ON_PUBLIC_REGISTER]
            if forbidden:
                raise AuthError(
                    code="FORBIDDEN_PRIVILEGED_ROLE_REGISTRATION",
                    message=f"Ochiq ro'yxatdan o'tishda imtiyozli rollar berilmaydi: {forbidden} (R-01)",
                    status_code=403,
                )

        user_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        totp_secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=") if enable_totp else None
        user = {
            "id": user_id,
            "display_name": display_name,
            "status": "ACTIVE",
            "password_hash": hash_password(password),
            "roles": requested_roles,
            "totp_secret": totp_secret,
            "adult_declared_at": now,
            "created_at": now,
        }
        self._persist_user(user)
        return dict(user)

    def seed_privileged_actor_session(
        self,
        *,
        user_id: str,
        roles: list[str],
        institution_id: str | None = None,
        organization_id: str | None = None,
    ) -> str:
        """Create a server-persisted user and session for administrative/testing fixtures."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        user = {
            "id": user_id,
            "display_name": f"Actor {user_id}",
            "status": "ACTIVE",
            "password_hash": hash_password("Fixture-Password-999!"),
            "roles": list(roles),
            "totp_secret": None,
            "adult_declared_at": now_iso,
            "created_at": now_iso,
        }
        self._persist_user(user)
        session_id = f"sess-{uuid4()}"
        session = {
            "session_id": session_id,
            "token_digest": _hash_session_token(session_id),
            "user_id": user_id,
            "roles": list(roles),
            "institution_id": institution_id,
            "organization_id": organization_id,
            "status": "ACTIVE",
            "created_at": now_iso,
            "expires_at": (now + timedelta(hours=12)).isoformat(),
            "revoked_at": None,
        }
        self._persist_session(session)
        return session_id

    def login(
        self,
        *,
        user_id: str,
        password: str,
        totp_code: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate a user against SQL storage and issue a persistent session (`DB-004`)."""
        user = self._load_user(user_id)
        if not user or not verify_password(password, user["password_hash"]):
            raise AuthError("INVALID_CREDENTIALS", "Login yoki parol noto'g'ri", status_code=401)

        if user["status"] != "ACTIVE":
            raise AuthError("USER_NOT_ACTIVE", f"Foydalanuvchi holati: {user['status']}", status_code=403)

        if user.get("totp_secret"):
            expected_totp = generate_totp_code(user["totp_secret"])
            if not totp_code or not hmac.compare_digest(totp_code, expected_totp):
                raise AuthError("TOTP_REQUIRED_OR_INVALID", "Ikki bosqichli TOTP kodi noto'g'ri", status_code=401)

        session_id = str(uuid4())
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        session = {
            "session_id": session_id,
            "token_digest": _hash_session_token(session_id),
            "user_id": user_id,
            "roles": list(user["roles"]),
            "status": "ACTIVE",
            "created_at": now_iso,
            "expires_at": (now + timedelta(hours=12)).isoformat(),
            "revoked_at": None,
        }
        self._persist_session(session)
        self._cache_session(session_id, session)
        return dict(session)

    def _cache_session(self, session_id: str, payload: dict[str, Any]) -> None:
        expires_at = time.monotonic() + settings.permission_cache_ttl_seconds
        self._l1_permission_cache[session_id] = (expires_at, dict(payload))

    def validate_session(self, session_id: str) -> dict[str, Any]:
        """Validate a session token against primary SQL DB and L1 cache (`TD-001` Section 6, `INV-15`)."""
        if session_id in self._revoked_sessions:
            raise AuthError("AUTH_REVOKED", "Sessiya yoki vakolat bekor qilingan (INV-15)", status_code=401)

        # Primary SQL check guarantees immediate cross-worker revocation & cross-process session sharing (R-03)
        session = self._load_session(session_id)
        if not session or session["status"] != "ACTIVE" or session.get("revoked_at") is not None:
            self._l1_permission_cache.pop(session_id, None)
            raise AuthError("AUTH_REVOKED", "Sessiya topilmadi yoki bekor qilingan", status_code=401)

        user = self._load_user(session["user_id"])
        if not user or user["status"] != "ACTIVE":
            self._l1_permission_cache.pop(session_id, None)
            raise AuthError("AUTH_REVOKED", "Foydalanuvchi faol emas", status_code=401)

        session["roles"] = list(user["roles"])
        self._cache_session(session_id, session)
        return dict(session)

    def revoke_session(
        self,
        *,
        session_id: str,
        actor_id: str,
        reason: str = "USER_LOGOUT",
        require_owner_user_id: str | None = None,
    ) -> dict[str, Any]:
        """Immediately revoke a session in SQL storage and evict L1 cache (`INV-15`, `API-061`)."""
        session = self._load_session(session_id)
        if not session:
            raise AuthError("SESSION_NOT_FOUND", "Sessiya topilmadi", status_code=404)

        if require_owner_user_id is not None and session["user_id"] != require_owner_user_id:
            raise AuthError(
                "FORBIDDEN_SESSION_SCOPE",
                "API-061: Foydalanuvchi faqat o'z sessiyasini bekor qila oladi",
                status_code=403,
            )

        session["status"] = "REVOKED"
        session["revoked_at"] = datetime.now(timezone.utc).isoformat()
        session["revoked_by"] = actor_id
        session["revoke_reason"] = reason
        self._persist_session(session)
        self._revoked_sessions.add(session_id)
        self._l1_permission_cache.pop(session_id, None)

        self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="SESSION_REVOKED_IMMEDIATE",
            entity_type="sessions",
            entity_id=session_id,
            metadata={"reason": reason, "user_id": session["user_id"]},
        )
        return dict(session)

    def revoke_all_user_sessions(self, *, user_id: str, actor_id: str, reason: str) -> int:
        """Immediately revoke all active sessions of `user_id` across SQL and L1 cache (`INV-15`)."""
        engine = get_engine()
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    select(sessions_table.c.session_id).where(
                        sessions_table.c.user_id == user_id,
                        sessions_table.c.status == "ACTIVE",
                    )
                )
                .scalars()
                .all()
            )
        active_ids = set(rows) | {
            sid for sid, sess in self.sessions.items() if sess["user_id"] == user_id and sess["status"] == "ACTIVE"
        }
        count = 0
        for sid in active_ids:
            self.revoke_session(session_id=sid, actor_id=actor_id, reason=reason)
            count += 1
        return count


auth_service = AuthSessionService()
