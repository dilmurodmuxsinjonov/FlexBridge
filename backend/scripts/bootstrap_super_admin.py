"""Idempotent CLI to bootstrap an initial FlexBridge Platform Super Admin (`ADMIN`).

Usage examples (from repo root or backend/):
    python backend/scripts/bootstrap_super_admin.py --email admin@example.uz --create --display-name "Platform Admin" --password-env SUPER_ADMIN_PASSWORD --enroll-totp
    python backend/scripts/bootstrap_super_admin.py --phone +998901234567 --days 3650
    python backend/scripts/bootstrap_super_admin.py --user-id <uuid>

Invariants enforced:
- Never hardcodes production passwords or secrets; reads password only from a named env var
  (`--password-env`) or interactive hidden prompt (`getpass`).
- Creates/reuses a dedicated non-login System Authority anchor user
  (`00000000-0000-0000-0000-000000000001`, `status='LIMITED'`, `password_hash=None`)
  so `platform_role_grants.chk_platform_grant_not_self` (`granted_by_id <> user_id`) holds cleanly.
- Idempotent: re-running for an already-active `ADMIN` returns the existing grant without duplicating rows.
- Logs `SUPER_ADMIN_BOOTSTRAPPED` to immutable `audit_events`.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.audit import AppendOnlyAuditStore  # noqa: E402
from app.core.iam_security import normalize_contact  # noqa: E402
from app.db.storage import init_storage, now, table, transaction  # noqa: E402
from app.services.auth import AuthError, auth_service, hash_password  # noqa: E402
from app.services.platform_admin import (  # noqa: E402
    PLATFORM_ROLE_DESCRIPTIONS,
    SYSTEM_AUTHORITY_USER_ID,
)

SYSTEM_AUTHORITY_DISPLAY_NAME = "FlexBridge System Authority"
DEFAULT_DAYS = 3650
MIN_PASSWORD_LEN = 12
MAX_PASSWORD_LEN = 1024


class BootstrapError(Exception):
    """Controlled failure raised by the Super Admin bootstrapper."""


def _fernet_cipher() -> Fernet:
    key = os.environ.get("MFA_ENCRYPTION_KEY", "").strip()
    if not key:
        raise BootstrapError("MFA_ENCRYPTION_KEY environment variable is required when --enroll-totp is enabled")
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise BootstrapError("MFA_ENCRYPTION_KEY is not a valid Fernet key") from exc


def _resolve_password(password_env: str | None, explicit_password: str | None) -> str:
    if explicit_password is not None:
        raw = explicit_password
    elif password_env:
        env_name = password_env.strip()
        if not env_name:
            raise BootstrapError("--password-env must name a non-empty environment variable")
        raw = os.environ.get(env_name, "")
        if not raw:
            raise BootstrapError(f"Environment variable '{env_name}' is not set or empty")
    else:
        if not sys.stdin.isatty():
            raise BootstrapError("Password is required for --create (pass --password-env VAR_NAME in non-interactive shells)")
        first = getpass.getpass("Super Admin password (min 12 chars): ")
        second = getpass.getpass("Confirm Super Admin password: ")
        if first != second:
            raise BootstrapError("Passwords do not match")
        raw = first

    if not (MIN_PASSWORD_LEN <= len(raw) <= MAX_PASSWORD_LEN):
        raise BootstrapError(f"Password length must be between {MIN_PASSWORD_LEN} and {MAX_PASSWORD_LEN} characters")
    return raw


def _ensure_system_authority_anchor(conn: Any) -> None:
    users = table("users")
    now_utc = now()
    anchor = conn.execute(
        select(users.c.id, users.c.status, users.c.password_hash)
        .where(users.c.id == SYSTEM_AUTHORITY_USER_ID)
        .with_for_update()
    ).mappings().first()
    if anchor is None:
        conn.execute(
            users.insert().values(
                id=SYSTEM_AUTHORITY_USER_ID,
                created_at=now_utc,
                updated_at=now_utc,
                display_name=SYSTEM_AUTHORITY_DISPLAY_NAME,
                status="LIMITED",
                password_hash=None,
                locale="uz",
                timezone="Asia/Tashkent",
                adult_declared_at=None,
                auth_version=1,
            )
        )
    elif anchor["status"] != "LIMITED" or anchor["password_hash"] is not None:
        conn.execute(
            users.update()
            .where(users.c.id == SYSTEM_AUTHORITY_USER_ID)
            .values(
                display_name=SYSTEM_AUTHORITY_DISPLAY_NAME,
                status="LIMITED",
                password_hash=None,
                updated_at=now_utc,
            )
        )


def _ensure_admin_role(conn: Any) -> str:
    roles = table("role_catalog")
    now_utc = now()
    conn.execute(
        insert(roles)
        .values(
            id=str(uuid4()),
            created_at=now_utc,
            updated_at=now_utc,
            code="ADMIN",
            scope_kind="PLATFORM",
            description=PLATFORM_ROLE_DESCRIPTIONS["ADMIN"],
        )
        .on_conflict_do_nothing(index_elements=["code"])
    )
    row = conn.execute(select(roles.c.id, roles.c.scope_kind).where(roles.c.code == "ADMIN")).mappings().one()
    if row["scope_kind"] != "PLATFORM":
        raise BootstrapError("role_catalog entry for ADMIN has non-PLATFORM scope_kind")
    return str(row["id"])


def bootstrap_super_admin(
    *,
    phone: str | None = None,
    email: str | None = None,
    user_id: str | None = None,
    create: bool = False,
    display_name: str | None = None,
    password_env: str | None = None,
    password: str | None = None,
    days: int = DEFAULT_DAYS,
    enroll_totp: bool = False,
) -> dict[str, Any]:
    """Idempotently bootstrap a Platform Super Admin (`ADMIN`) and optionally enroll TOTP."""
    if not (phone or email or user_id):
        raise BootstrapError("Specify at least one target selector: --phone, --email, or --user-id")
    if type(days) is not int or not (1 <= days <= 3650):
        raise BootstrapError("--days must be an integer between 1 and 3650")

    parsed_uid: str | None = None
    if user_id:
        try:
            parsed_uid = str(UUID(user_id.strip()))
        except ValueError as exc:
            raise BootstrapError("--user-id must be a valid UUID") from exc
        if parsed_uid == SYSTEM_AUTHORITY_USER_ID:
            raise BootstrapError("Cannot grant ADMIN to the System Authority anchor account")

    contacts_to_bind: list[tuple[str, str]] = []
    if phone:
        try:
            contacts_to_bind.append(("PHONE", normalize_contact("PHONE", phone)))
        except AuthError as exc:
            raise BootstrapError(f"Invalid --phone: {exc}") from exc
    if email:
        try:
            contacts_to_bind.append(("EMAIL", normalize_contact("EMAIL", email)))
        except AuthError as exc:
            raise BootstrapError(f"Invalid --email: {exc}") from exc

    audit = AppendOnlyAuditStore()

    with transaction() as conn:
        _ensure_system_authority_anchor(conn)
        admin_role_id = _ensure_admin_role(conn)

        t_users = table("users")
        t_contacts = table("user_contacts")
        t_grants = table("platform_role_grants")
        t_mfa = table("mfa_credentials")

        matched_user_ids: set[str] = set()
        for channel, norm_val in contacts_to_bind:
            existing_contact = conn.execute(
                select(t_contacts.c.user_id, t_contacts.c.revoked_at)
                .where(t_contacts.c.channel == channel, t_contacts.c.normalized_value == norm_val)
                .with_for_update()
            ).mappings().first()
            if existing_contact and existing_contact["revoked_at"] is None:
                matched_user_ids.add(str(existing_contact["user_id"]))

        if len(matched_user_ids) > 1:
            raise BootstrapError("--phone and --email resolve to different existing user accounts")

        contact_uid = next(iter(matched_user_ids), None)
        if parsed_uid and contact_uid and parsed_uid != contact_uid:
            raise BootstrapError("--user-id does not match the user resolved from --phone/--email")

        resolved_uid = parsed_uid or contact_uid
        user_row = (
            conn.execute(select(t_users).where(t_users.c.id == resolved_uid).with_for_update()).mappings().first()
            if resolved_uid
            else None
        )

        created_user = False
        now_utc = now()
        if user_row is None:
            if not create:
                raise BootstrapError("Target user not found (pass --create to provision a new Super Admin user)")
            clean_name = (display_name or "Platform Super Admin").strip()
            if not (2 <= len(clean_name) <= 120):
                raise BootstrapError("--display-name must be 2..120 characters")
            secret_password = _resolve_password(password_env, password)
            new_uid = parsed_uid or str(uuid4())
            conn.execute(
                t_users.insert().values(
                    id=new_uid,
                    created_at=now_utc,
                    updated_at=now_utc,
                    display_name=clean_name,
                    status="ACTIVE",
                    password_hash=hash_password(secret_password),
                    locale="uz",
                    timezone="Asia/Tashkent",
                    adult_declared_at=now_utc,
                    auth_version=1,
                )
            )
            conn.execute(
                table("candidate_profiles").insert().values(
                    id=str(uuid4()),
                    created_at=now_utc,
                    updated_at=now_utc,
                    user_id=new_uid,
                    headline=clean_name,
                    region="",
                    experience_months=0,
                    visibility="PRIVATE",
                )
            )
            for idx, (channel, norm_val) in enumerate(contacts_to_bind):
                conn.execute(
                    insert(t_contacts)
                    .values(
                        id=str(uuid4()),
                        created_at=now_utc,
                        updated_at=now_utc,
                        user_id=new_uid,
                        channel=channel,
                        normalized_value=norm_val,
                        verified_at=now_utc,
                        revoked_at=None,
                        is_primary=(idx == 0),
                    )
                    .on_conflict_do_update(
                        index_elements=["channel", "normalized_value"],
                        set_={
                            "user_id": new_uid,
                            "verified_at": now_utc,
                            "revoked_at": None,
                            "is_primary": (idx == 0),
                            "updated_at": now_utc,
                        },
                    )
                )
            resolved_uid = new_uid
            created_user = True
            user_row = conn.execute(select(t_users).where(t_users.c.id == resolved_uid)).mappings().one()
        else:
            resolved_uid = str(user_row["id"])
            if resolved_uid == SYSTEM_AUTHORITY_USER_ID:
                raise BootstrapError("Cannot grant ADMIN to the System Authority anchor account")
            if user_row["status"] != "ACTIVE":
                raise BootstrapError(f"Target user {resolved_uid} status is {user_row['status']}; must be ACTIVE")

        active_grant = conn.execute(
            select(t_grants.c.id, t_grants.c.expires_at)
            .where(
                t_grants.c.user_id == resolved_uid,
                t_grants.c.role_id == admin_role_id,
                t_grants.c.revoked_at.is_(None),
                t_grants.c.expires_at > now_utc,
            )
            .order_by(t_grants.c.expires_at.desc())
            .limit(1)
            .with_for_update()
        ).mappings().first()

        grant_created = False
        if active_grant is not None:
            grant_id = str(active_grant["id"])
            expires_at = active_grant["expires_at"]
        else:
            grant_id = str(uuid4())
            expires_at = now_utc + timedelta(days=days)
            conn.execute(
                t_grants.insert().values(
                    id=grant_id,
                    created_at=now_utc,
                    updated_at=now_utc,
                    user_id=resolved_uid,
                    role_id=admin_role_id,
                    granted_by_id=SYSTEM_AUTHORITY_USER_ID,
                    expires_at=expires_at,
                    revoked_at=None,
                )
            )
            grant_created = True
            audit.append_audit_event(
                actor_id=SYSTEM_AUTHORITY_USER_ID,
                action="SUPER_ADMIN_BOOTSTRAPPED",
                entity_type="platform_role_grant",
                entity_id=grant_id,
                metadata={
                    "target_user_id": resolved_uid,
                    "role_code": "ADMIN",
                    "days": days,
                    "expires_at": expires_at.isoformat(),
                    "created_user": created_user,
                },
            )

        otpauth_uri: str | None = None
        totp_already_enrolled = False
        if enroll_totp:
            existing_totp = conn.execute(
                select(t_mfa.c.id)
                .where(
                    t_mfa.c.user_id == resolved_uid,
                    t_mfa.c.kind == "TOTP",
                    t_mfa.c.verified_at.is_not(None),
                    t_mfa.c.revoked_at.is_(None),
                )
                .with_for_update()
            ).first()
            if existing_totp is not None:
                totp_already_enrolled = True
            else:
                fernet = _fernet_cipher()
                secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
                conn.execute(
                    t_mfa.insert().values(
                        id=str(uuid4()),
                        created_at=now_utc,
                        updated_at=now_utc,
                        user_id=resolved_uid,
                        kind="TOTP",
                        credential_key=str(uuid4()),
                        secret_encrypted=fernet.encrypt(secret.encode()).decode(),
                        sign_count=0,
                        verified_at=now_utc,
                        revoked_at=None,
                    )
                )
                if not created_user:
                    auth_service.rotate_security(conn, resolved_uid)
                audit.append_audit_event(
                    actor_id=SYSTEM_AUTHORITY_USER_ID,
                    action="MFA_TOTP_BOOTSTRAPPED",
                    entity_type="user",
                    entity_id=resolved_uid,
                    metadata={"source": "bootstrap_super_admin"},
                )
                label = contacts_to_bind[0][1] if contacts_to_bind else resolved_uid
                otpauth_uri = (
                    f"otpauth://totp/{quote('FlexBridge:' + label)}"
                    f"?secret={secret}&issuer=FlexBridge&algorithm=SHA1&digits=6&period=30"
                )

    result: dict[str, Any] = {
        "ok": True,
        "user_id": resolved_uid,
        "display_name": user_row["display_name"],
        "system_authority_id": SYSTEM_AUTHORITY_USER_ID,
        "grant_id": grant_id,
        "role_code": "ADMIN",
        "expires_at": expires_at.isoformat(),
        "created_user": created_user,
        "grant_created": grant_created,
        "idempotent_noop": not grant_created,
        "totp_already_enrolled": totp_already_enrolled,
    }
    if otpauth_uri is not None:
        result["otpauth_uri"] = otpauth_uri
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Idempotently bootstrap a FlexBridge Platform Super Admin (ADMIN) account.",
    )
    parser.add_argument("--phone", help="Verified user phone in international format (+998...)")
    parser.add_argument("--email", help="Verified user email address")
    parser.add_argument("--user-id", help="Existing or new user UUID")
    parser.add_argument("--create", action="store_true", help="Create the user if it does not exist yet")
    parser.add_argument("--display-name", help="Display name when creating a new user")
    parser.add_argument(
        "--password-env",
        help="Name of environment variable holding the initial password for --create (never pass secret directly)",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Grant validity in days (1..3650, default 3650)")
    parser.add_argument(
        "--enroll-totp",
        action="store_true",
        help="Enroll verified TOTP MFA if absent and print otpauth:// URI",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        init_storage()
        result = bootstrap_super_admin(
            phone=args.phone,
            email=args.email,
            user_id=args.user_id,
            create=args.create,
            display_name=args.display_name,
            password_env=args.password_env,
            days=args.days,
            enroll_totp=args.enroll_totp,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
