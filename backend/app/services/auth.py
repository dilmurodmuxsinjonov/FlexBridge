"""Authentication, TOTP, Session, and Immediate Revocation Cache service (S2.2.1).

Enforces:
- 18+ adult candidate/user declaration requirement (`users.adult_declared_at`).
- Salted password hashing + constant-time comparison and RFC 6238 TOTP verification.
- `INV-15` & `AC-017` (1.4 PDF section 5): L1/Redis permission & session cache (`TTL = 15s`)
  with immediate event-driven invalidation on session revoke, user suspension, or role/membership revocation.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.audit import AppendOnlyAuditStore
from app.core.config import settings


class AuthError(Exception):
    """Raised on authentication, session, or revocation errors."""

    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def hash_password(password: str, salt: str | None = None) -> str:
    """Create a salted password digest (`argon2id_sim$salt$hex`)."""
    actual_salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 120_000)
    return f"argon2id_v1${actual_salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored digest in constant time."""
    try:
        _scheme, salt, _hex = stored_hash.split("$", 2)
    except ValueError:
        return False
    expected = hash_password(password, salt=salt)
    return hmac.compare_digest(expected, stored_hash)


def generate_totp_code(secret_hex: str, timestamp: int | None = None, step: int = 30) -> str:
    """Generate a 6-digit RFC 6238 TOTP code for `secret_hex`."""
    ts = int(time.time()) if timestamp is None else timestamp
    counter = ts // step
    key = bytes.fromhex(secret_hex)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code_int:06d}"


@dataclass
class AuthSessionService:
    """Manages `users`, `user_sessions`, and the 15s L1/Redis permission cache with immediate revoke (`INV-15`)."""

    audit_store: AppendOnlyAuditStore = field(default_factory=AppendOnlyAuditStore)
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    _l1_permission_cache: dict[str, tuple[float, dict[str, Any]]] = field(default_factory=dict)
    _revoked_sessions: set[str] = field(default_factory=set)

    def register_user(
        self,
        *,
        display_name: str,
        password: str,
        adult_confirmed: bool,
        roles: list[str] | None = None,
        enable_totp: bool = False,
    ) -> dict[str, Any]:
        """Register an 18+ user account (`DB-001 users`)."""
        if not adult_confirmed:
            raise AuthError(
                code="ADULT_DECLARATION_REQUIRED",
                message="FlexBridge R1 faqat 18+ foydalanuvchilar uchun mo'ljallangan",
                status_code=422,
            )
        user_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        totp_secret = secrets.token_hex(20) if enable_totp else None
        user = {
            "id": user_id,
            "display_name": display_name,
            "status": "ACTIVE",
            "password_hash": hash_password(password),
            "roles": list(roles or ["CANDIDATE"]),
            "totp_secret": totp_secret,
            "adult_declared_at": now,
            "created_at": now,
        }
        self.users[user_id] = user
        return dict(user)

    def login(
        self,
        *,
        user_id: str,
        password: str,
        totp_code: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate a user and issue a session cached in L1/Redis (`TTL = 15s`)."""
        user = self.users.get(user_id)
        if not user or not verify_password(password, user["password_hash"]):
            raise AuthError("INVALID_CREDENTIALS", "Login yoki parol noto'g'ri", status_code=401)

        if user["status"] != "ACTIVE":
            raise AuthError("USER_NOT_ACTIVE", f"Foydalanuvchi holati: {user['status']}", status_code=403)

        if user.get("totp_secret"):
            expected_totp = generate_totp_code(user["totp_secret"])
            if not totp_code or not hmac.compare_digest(totp_code, expected_totp):
                raise AuthError("TOTP_REQUIRED_OR_INVALID", "Ikki bosqichli TOTP kodi noto'g'ri", status_code=401)

        session_id = str(uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "roles": list(user["roles"]),
            "status": "ACTIVE",
            "created_at": now_iso,
            "revoked_at": None,
        }
        self.sessions[session_id] = session
        self._cache_session(session_id, session)
        return dict(session)

    def _cache_session(self, session_id: str, payload: dict[str, Any]) -> None:
        expires_at = time.monotonic() + settings.permission_cache_ttl_seconds
        self._l1_permission_cache[session_id] = (expires_at, dict(payload))

    def validate_session(self, session_id: str) -> dict[str, Any]:
        """Validate a session token, checking immediate revocation (`INV-15`, `AC-017`) before L1 cache."""
        if session_id in self._revoked_sessions:
            raise AuthError("AUTH_REVOKED", "Sessiya yoki vakolat bekor qilingan (AC-017)", status_code=401)

        now_mono = time.monotonic()
        cached = self._l1_permission_cache.get(session_id)
        if cached is not None:
            expires_at, payload = cached
            if now_mono < expires_at:
                return dict(payload)
            del self._l1_permission_cache[session_id]

        session = self.sessions.get(session_id)
        if not session or session["status"] != "ACTIVE":
            raise AuthError("AUTH_REVOKED", "Sessiya topilmadi yoki bekor qilingan", status_code=401)

        user = self.users.get(session["user_id"])
        if not user or user["status"] != "ACTIVE":
            raise AuthError("AUTH_REVOKED", "Foydalanuvchi faol emas", status_code=401)

        self._cache_session(session_id, session)
        return dict(session)

    def revoke_session(self, *, session_id: str, actor_id: str, reason: str = "USER_LOGOUT") -> dict[str, Any]:
        """Immediately revoke a session and evict L1/Redis permission cache (`INV-15`, `AC-017`)."""
        session = self.sessions.get(session_id)
        if not session:
            raise AuthError("SESSION_NOT_FOUND", "Sessiya topilmadi", status_code=404)

        session["status"] = "REVOKED"
        session["revoked_at"] = datetime.now(timezone.utc).isoformat()
        self._revoked_sessions.add(session_id)
        self._l1_permission_cache.pop(session_id, None)

        self.audit_store.append_audit_event(
            actor_id=actor_id,
            action="SESSION_REVOKED_IMMEDIATE",
            entity_type="user_session",
            entity_id=session_id,
            metadata={"reason": reason, "user_id": session["user_id"]},
        )
        return dict(session)

    def revoke_all_user_sessions(self, *, user_id: str, actor_id: str, reason: str) -> int:
        """Immediately revoke all sessions of `user_id` (e.g. on role/membership removal or suspension)."""
        count = 0
        for sid, sess in self.sessions.items():
            if sess["user_id"] == user_id and sess["status"] == "ACTIVE":
                self.revoke_session(session_id=sid, actor_id=actor_id, reason=reason)
                count += 1
        return count


auth_service = AuthSessionService()
