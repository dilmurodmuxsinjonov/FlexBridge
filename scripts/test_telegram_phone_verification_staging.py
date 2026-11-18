#!/usr/bin/env python3
"""FlexBridge 1.4 Telegram Bot Phone Verification & OTP Choice Staging Suite (FB-196).

Verifies end-to-end against live Docker staging stack via PgBouncer and Next.js BFF:
Phase 1: Auth Options Delivery Methods (GET /api/bff/auth/options -> SMS & TELEGRAM, telegram_bot_username).
Phase 2: Telegram Challenge Issuance (POST /api/bff/auth/challenges with delivery_method=TELEGRAM -> 202 AWAITING_TELEGRAM_CONTACT).
Phase 3: Pre-Verification Status Check (GET /api/bff/auth/challenges/[id]/status -> telegram_verified=False).
Phase 4: Premature OTP Consume Block (POST /api/bff/auth/challenges/[id]/consume before bot contact -> 403 TELEGRAM_CONTACT_REQUIRED).
Phase 5: Bot Startup Prompt (/start <challenge_id> -> ReplyKeyboardMarkup with request_contact=True).
Phase 6: Reject Plain Text Phone Number (POST /api/bff/auth/telegram/webhook without contact object -> 422 TELEGRAM_NATIVE_CONTACT_REQUIRED).
Phase 7: Reject Spoofed/Forwarded Contact Card (contact.user_id != message.from.id -> 403 TELEGRAM_CONTACT_OWNERSHIP_MISMATCH).
Phase 8: Reject Website vs Telegram Phone Mismatch (website_phone != telegram_phone -> 409 TELEGRAM_PHONE_MISMATCH).
Phase 9: Accept Matching Telegram Contact & Deliver OTP (website_phone == telegram_phone -> 200 CONTACT_VERIFIED_OTP_DELIVERED).
Phase 10: Complete Registration with Verified Telegram OTP & Verify /royxatdan-otish SSR UI.

Target DB: Strictly PgBouncer on 127.0.0.1:5432/flexbridge with prepare_threshold=None; ZERO queries to pg_live.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import dotenv_values

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
infra_env = dotenv_values(Path(REPO_ROOT) / "infra" / ".env")
for k, v in infra_env.items():
    if k and v and k not in os.environ:
        os.environ[k] = v

BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from app.core.iam_security import decrypt

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
STAGING_DB_URL = os.environ.get(
    "STAGING_DB_URL",
    "postgresql+psycopg://flexbridge_owner:stg_secure_pg_pass_2026_flexbridge_isolated@127.0.0.1:5432/flexbridge",
)

engine = create_engine(STAGING_DB_URL, connect_args={"prepare_threshold": None})


def make_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    cookie_jar: http.cookiejar.CookieJar | None = None,
) -> tuple[int, dict[str, Any] | str, dict[str, str]]:
    req_headers = headers or {}
    if cookie_jar is not None:
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    else:
        opener = urllib.request.build_opener()

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with opener.open(req, timeout=15) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            body = resp.read().decode("utf-8")
            try:
                return status, json.loads(body), resp_headers
            except Exception:
                return status, body, resp_headers
    except urllib.error.HTTPError as exc:
        status = exc.code
        resp_headers = dict(exc.headers)
        body = exc.read().decode("utf-8")
        try:
            return status, json.loads(body), resp_headers
        except Exception:
            return status, body, resp_headers


def main() -> None:
    print("=" * 76)
    print("  FB-196: TELEGRAM BOT PHONE VERIFICATION & OTP CHOICE STAGING SUITE")
    print("=" * 76)

    # Reset rate limits before suite
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE flexbridge.auth_rate_limits"))

    # -------------------------------------------------------------------------
    # Phase 1: Auth Options Delivery Methods
    # -------------------------------------------------------------------------
    print("\n--- Phase 1: Auth Options Delivery Methods (GET /api/bff/auth/options) ---")
    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/auth/options")
    assert status == 200 and isinstance(body, dict), f"Phase 1 failed ({status}): {body}"
    options_mode = str(body.get("telegram_mode") or "SIMULATION").upper()
    delivery_methods = body.get("delivery_methods", [])
    assert "SMS" in delivery_methods and "TELEGRAM" in delivery_methods, (
        f"Expected SMS and TELEGRAM in delivery_methods, got {delivery_methods}"
    )
    assert body.get("telegram_bot_username"), f"Expected telegram_bot_username, got {body}"
    print(f"  OK: mode={options_mode}, delivery_methods={delivery_methods}, bot=@{body.get('telegram_bot_username')}")

    # -------------------------------------------------------------------------
    # Phase 2: Issue TELEGRAM Challenge
    # -------------------------------------------------------------------------
    print("\n--- Phase 2: Issue TELEGRAM Challenge (POST /api/bff/auth/challenges) ---")
    website_phone = f"+99890{random.randint(1000000, 9999999)}"
    mismatched_phone = f"+99891{random.randint(1000000, 9999999)}"
    tg_user_id = random.randint(200000000, 899999999)

    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "channel": "PHONE",
                "destination": website_phone,
                "purpose": "REGISTER",
                "delivery_method": "TELEGRAM",
            }
        ).encode(),
    )
    assert status == 202 and isinstance(body, dict), f"Phase 2 failed ({status}): {body}"
    assert body.get("delivery_method") == "TELEGRAM", f"Expected TELEGRAM, got {body}"
    assert body.get("status") == "AWAITING_TELEGRAM_CONTACT", f"Expected AWAITING_TELEGRAM_CONTACT, got {body}"
    challenge_id = body.get("challenge_id")
    assert challenge_id and body.get("telegram_deep_link"), f"Missing challenge_id or deep link: {body}"
    print(f"  OK: Issued TELEGRAM challenge {challenge_id} for {website_phone}")

    # Read actual OTP from DB to verify Phase 4 blocks even the real OTP before Telegram contact verification
    with engine.begin() as conn:
        row = (
            conn.execute(
                text("SELECT delivery_encrypted FROM flexbridge.auth_challenges WHERE id = :cid"),
                {"cid": challenge_id},
            )
            .mappings()
            .first()
        )
        assert row and row["delivery_encrypted"], "Expected delivery_encrypted in DB"
        real_otp = decrypt(row["delivery_encrypted"])["code"]

    # -------------------------------------------------------------------------
    # Phase 3: Pre-Verification Status Check
    # -------------------------------------------------------------------------
    print("\n--- Phase 3: Pre-Verification Status Check (GET /api/bff/auth/challenges/[id]/status) ---")
    status, body, _ = make_request(f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/status")
    assert status == 200 and isinstance(body, dict), f"Phase 3 failed ({status}): {body}"
    assert body.get("delivery_method") == "TELEGRAM", f"Expected TELEGRAM, got {body}"
    assert body.get("telegram_verified") is False, f"Expected telegram_verified=False, got {body}"
    print("  OK: Challenge status confirms telegram_verified=False prior to bot contact.")

    # -------------------------------------------------------------------------
    # Phase 4: Premature OTP Consume Guard (403 TELEGRAM_CONTACT_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 4: Premature OTP Consume Guard (403 TELEGRAM_CONTACT_REQUIRED) ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/consume",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"purpose": "REGISTER", "code": real_otp}).encode(),
    )
    assert status == 403 and isinstance(body, dict), f"Expected 403, got {status}: {body}"
    assert body.get("error") == "TELEGRAM_CONTACT_REQUIRED", f"Expected TELEGRAM_CONTACT_REQUIRED, got {body}"
    print("  OK: Consuming OTP before Telegram contact verification blocked (403 TELEGRAM_CONTACT_REQUIRED).")

    if options_mode == "LIVE":
        print("\n--- Phase 5 (LIVE): Unauthenticated Webhook Spoof Rejection ---")
        wh_status, wh_body, _ = make_request(
            f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
            method="POST",
            headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
            data=json.dumps(
                {
                    "challenge_id": challenge_id,
                    "message": {
                        "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                        "chat": {"id": tg_user_id, "type": "private"},
                        "text": f"/start {challenge_id}",
                    },
                }
            ).encode(),
        )
        assert wh_status in (403, 503), f"LIVE mode must reject unsigned webhook calls, got {wh_status}: {wh_body}"
        assert not (isinstance(wh_body, dict) and wh_body.get("otp_code")), "LIVE mode must never echo OTP"

        ssr_status, ssr_html, _ = make_request(f"{FRONTEND_URL}/royxatdan-otish")
        assert ssr_status == 200 and isinstance(ssr_html, str)
        assert "Ro‘yxatdan O‘tish" in ssr_html or "FlexBridge" in ssr_html
        print("  OK: LIVE Telegram bot (@FlexBridgeAuthBot) webhook guards and /royxatdan-otish SSR verified.")
        print("\n" + "=" * 76)
        print("  ALL LIVE-MODE TELEGRAM PHONE VERIFICATION CHECKS PASSED 100% GREEN!")
        print("=" * 76)
        return

    # -------------------------------------------------------------------------
    # Phase 5: Bot Startup Prompt (/start <challenge_id> -> request_contact=True)
    # -------------------------------------------------------------------------
    print("\n--- Phase 5: Telegram Bot /start Prompt (request_contact=True) ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "challenge_id": challenge_id,
                "message": {
                    "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                    "chat": {"id": tg_user_id, "type": "private"},
                    "text": f"/start {challenge_id}",
                },
            }
        ).encode(),
    )
    assert status == 200 and isinstance(body, dict), f"Phase 5 failed ({status}): {body}"
    assert body.get("step") == "AWAITING_CONTACT", f"Expected AWAITING_CONTACT, got {body}"
    kb = body.get("reply_markup", {}).get("keyboard", [[]])
    assert kb and kb[0][0].get("request_contact") is True, f"Expected request_contact=True keyboard, got {kb}"
    print("  OK: Bot /start returned native ReplyKeyboardMarkup with request_contact=True.")

    # -------------------------------------------------------------------------
    # Phase 6: Reject Manually Typed Phone Text (422 TELEGRAM_NATIVE_CONTACT_REQUIRED)
    # -------------------------------------------------------------------------
    print("\n--- Phase 6: Reject Plain Text Phone Number (422 TELEGRAM_NATIVE_CONTACT_REQUIRED) ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "challenge_id": challenge_id,
                "message": {
                    "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                    "chat": {"id": tg_user_id, "type": "private"},
                    "text": website_phone,
                },
            }
        ).encode(),
    )
    assert status == 422 and isinstance(body, dict), f"Expected 422, got {status}: {body}"
    assert body.get("error") == "TELEGRAM_NATIVE_CONTACT_REQUIRED", (
        f"Expected TELEGRAM_NATIVE_CONTACT_REQUIRED, got {body}"
    )
    print("  OK: Plain text phone message rejected (422 TELEGRAM_NATIVE_CONTACT_REQUIRED).")

    # -------------------------------------------------------------------------
    # Phase 7: Reject Forwarded Contact Belonging to Another User (403)
    # -------------------------------------------------------------------------
    print("\n--- Phase 7: Reject Forwarded Contact Card (403 TELEGRAM_CONTACT_OWNERSHIP_MISMATCH) ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "challenge_id": challenge_id,
                "message": {
                    "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                    "chat": {"id": tg_user_id, "type": "private"},
                    "contact": {
                        "phone_number": website_phone,
                        "first_name": "OtherUser",
                        "user_id": tg_user_id + 999,
                    },
                },
            }
        ).encode(),
    )
    assert status == 403 and isinstance(body, dict), f"Expected 403, got {status}: {body}"
    assert body.get("error") == "TELEGRAM_CONTACT_OWNERSHIP_MISMATCH", (
        f"Expected TELEGRAM_CONTACT_OWNERSHIP_MISMATCH, got {body}"
    )
    print("  OK: Spoofed/forwarded contact card rejected (403 TELEGRAM_CONTACT_OWNERSHIP_MISMATCH).")

    # -------------------------------------------------------------------------
    # Phase 8: Reject Website vs Telegram Phone Mismatch (409 TELEGRAM_PHONE_MISMATCH)
    # -------------------------------------------------------------------------
    print("\n--- Phase 8: Reject Website vs Telegram Phone Mismatch (409 TELEGRAM_PHONE_MISMATCH) ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "challenge_id": challenge_id,
                "message": {
                    "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                    "chat": {"id": tg_user_id, "type": "private"},
                    "contact": {
                        "phone_number": mismatched_phone,
                        "first_name": "Dilmurod",
                        "user_id": tg_user_id,
                    },
                },
            }
        ).encode(),
    )
    assert status == 409 and isinstance(body, dict), f"Expected 409, got {status}: {body}"
    assert body.get("error") == "TELEGRAM_PHONE_MISMATCH", f"Expected TELEGRAM_PHONE_MISMATCH, got {body}"
    print(f"  OK: Mismatched phone ({mismatched_phone} != {website_phone}) rejected (409 TELEGRAM_PHONE_MISMATCH).")

    # -------------------------------------------------------------------------
    # Phase 9: Accept Matching Telegram Contact & Deliver OTP
    # -------------------------------------------------------------------------
    print("\n--- Phase 9: Accept Matching Contact & Deliver OTP (200 CONTACT_VERIFIED_OTP_DELIVERED) ---")
    # Test also without leading '+' since Telegram often sends "998901234567"
    tg_formatted_phone = website_phone.lstrip("+")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/telegram/webhook",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "challenge_id": challenge_id,
                "message": {
                    "from": {"id": tg_user_id, "first_name": "Dilmurod"},
                    "chat": {"id": tg_user_id, "type": "private"},
                    "contact": {
                        "phone_number": tg_formatted_phone,
                        "first_name": "Dilmurod",
                        "user_id": tg_user_id,
                    },
                },
            }
        ).encode(),
    )
    assert status == 200 and isinstance(body, dict), f"Phase 9 failed ({status}): {body}"
    assert body.get("step") == "CONTACT_VERIFIED_OTP_DELIVERED", f"Unexpected step: {body}"
    assert body.get("telegram_verified") is True, f"Expected telegram_verified=True: {body}"
    delivered_otp = body.get("otp_code")
    assert delivered_otp == real_otp, f"Expected OTP {real_otp}, got {delivered_otp}"

    # Verify status endpoint now reports telegram_verified=True and delivery_status=SENT
    st_code, st_body, _ = make_request(f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/status")
    assert st_code == 200 and isinstance(st_body, dict), f"Status check failed: {st_body}"
    assert st_body.get("telegram_verified") is True, f"Expected telegram_verified=True in status: {st_body}"
    assert st_body.get("delivery_status") == "SENT", f"Expected delivery_status=SENT in status: {st_body}"
    print(f"  OK: Matching phone ({website_phone}) verified and 6-digit OTP delivered via Telegram bot.")

    # -------------------------------------------------------------------------
    # Phase 10: Consume OTP, Complete Registration & Verify /royxatdan-otish SSR
    # -------------------------------------------------------------------------
    print("\n--- Phase 10: Consume Telegram OTP, Register User & Verify SSR UI ---")
    status, body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/challenges/{challenge_id}/consume",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps({"purpose": "REGISTER", "code": delivered_otp}).encode(),
    )
    assert status == 200 and isinstance(body, dict), f"Consume failed ({status}): {body}"
    verification_token = body.get("verification_token")
    assert verification_token, f"Expected verification_token, got {body}"

    jar = http.cookiejar.CookieJar()
    reg_password = f"TgVerified_{uuid4().hex[:8]}!"
    status, reg_body, _ = make_request(
        f"{FRONTEND_URL}/api/bff/auth/register",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": FRONTEND_URL},
        data=json.dumps(
            {
                "verification_token": verification_token,
                "display_name": "Telegram Verified Nomzod",
                "password": reg_password,
                "adult_confirmed": True,
                "terms_version": "2026.1",
                "privacy_version": "2026.1",
                "roles": ["CANDIDATE"],
            }
        ).encode(),
        cookie_jar=jar,
    )
    assert status == 201 and isinstance(reg_body, dict) and reg_body.get("ok") is True, (
        f"Registration failed ({status}): {reg_body}"
    )

    ssr_status, ssr_html, _ = make_request(f"{FRONTEND_URL}/royxatdan-otish")
    assert ssr_status == 200 and isinstance(ssr_html, str), f"Expected 200 SSR on /royxatdan-otish, got {ssr_status}"
    assert "Ro‘yxatdan O‘tish" in ssr_html or "FlexBridge" in ssr_html, "Expected registration page HTML"
    print("  OK: Candidate registered via Telegram-verified OTP and /royxatdan-otish SSR verified.")

    print("\n" + "=" * 76)
    print("  ALL 10 PHASES OF TELEGRAM PHONE VERIFICATION PASSED 100% GREEN!")
    print("=" * 76)


if __name__ == "__main__":
    main()
