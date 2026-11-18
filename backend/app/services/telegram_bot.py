"""Telegram Bot Phone Contact Verification & OTP Delivery Service.

Enforces within Telegram Bot capabilities:
1. On /start (or /start <challenge_id>), prompts the user with a native
   ReplyKeyboardMarkup button (request_contact=True) to share their verified
   Telegram phone number.
2. Rejects manually typed text phone numbers (TELEGRAM_NATIVE_CONTACT_REQUIRED).
3. Verifies contact ownership: message.contact.user_id == message.from.id
   (TELEGRAM_CONTACT_OWNERSHIP_MISMATCH) to prevent forwarded contact spoofing.
4. Verifies strict phone equality: normalized Telegram contact phone number
   MUST match the phone number entered on the FlexBridge website for the active
   challenge (TELEGRAM_PHONE_MISMATCH).
5. Upon verification, marks the challenge as SENT + telegram_verified=True and
   delivers the 6-digit OTP code via Telegram.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx
from sqlalchemy import select

from app.core.audit import AppendOnlyAuditStore
from app.core.iam_security import decrypt, digest, encrypt, normalize_contact, rate_limit
from app.db.storage import load_domain_record, now, save_domain_record, table, transaction
from app.services.auth import AuthError

logger = logging.getLogger(__name__)
# Suppress httpx/httpcore INFO request URL logs so TELEGRAM_BOT_TOKEN never leaks into stdout logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
audit = AppendOnlyAuditStore()

TELEGRAM_SESSION_NAMESPACE = "telegram_bot_session"


_RESOLVED_USERNAME: dict[str, str] = {}


def get_bot_username() -> str:
    """Bot @username for deep links: TELEGRAM_BOT_USERNAME, else resolved once via getMe."""
    configured = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    if configured:
        return configured
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        if token not in _RESOLVED_USERNAME:
            api_base = os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip("/")
            try:
                with httpx.Client(timeout=5.0, follow_redirects=False) as client:
                    data = client.get(f"{api_base}/bot{token}/getMe").json()
                username = (data.get("result") or {}).get("username") if data.get("ok") else None
            except Exception as exc:
                logger.warning("Telegram getMe failed (%s)", type(exc).__name__)
                username = None
            if not username:
                return "FlexBridgeAuthBot"
            _RESOLVED_USERNAME[token] = str(username)
        return _RESOLVED_USERNAME[token]
    return "FlexBridgeAuthBot"


def telegram_mode() -> str:
    """LIVE when a bot token is configured; SIMULATION only when explicitly enabled
    for local staging tests (and never alongside a real token); otherwise DISABLED.

    In SIMULATION the webhook is unauthenticated and echoes the OTP so scripted
    tests can run without Telegram. It must never be enabled on a public host.
    """
    if os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
        return "LIVE"
    if os.environ.get("TELEGRAM_SIMULATION_MODE", "").strip().lower() in ("1", "true", "yes"):
        return "SIMULATION"
    return "DISABLED"


# Fields that may leave the backend in LIVE mode: never the OTP or the bot text that contains it.
PUBLIC_RESULT_FIELDS = ("ok", "step", "telegram_verified", "delivery_status")


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    return {key: result[key] for key in PUBLIC_RESULT_FIELDS if key in result}


def _normalize_telegram_phone(raw_phone: str) -> str:
    cleaned = re.sub(r"[ ()-]", "", str(raw_phone or "").strip())
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return normalize_contact("PHONE", cleaned)


def _send_telegram_api_message(chat_id: int | str, text: str, reply_markup: dict[str, Any] | None = None) -> bool:
    """If TELEGRAM_BOT_TOKEN is configured in env, dispatches sendMessage to api.telegram.org."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    api_base = os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip("/")
    if not token:
        return False
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            resp = client.post(f"{api_base}/bot{token}/sendMessage", json=payload)
            return resp.status_code == 200
    except Exception as exc:
        logger.warning("Telegram API sendMessage failed (%s)", type(exc).__name__)
        return False


class TelegramBotVerificationService:
    def handle_update(
        self,
        *,
        update: dict[str, Any],
        ip: str = "unknown",
        explicit_challenge_id: str | None = None,
    ) -> dict[str, Any]:
        rate_limit("telegram-webhook-ip", ip, 60, 600)

        message = update.get("message")
        if not isinstance(message, dict):
            raise AuthError("INVALID_TELEGRAM_UPDATE", "Telegram message payload is required", 422)

        from_user = message.get("from")
        if not isinstance(from_user, dict) or from_user.get("id") is None:
            raise AuthError("INVALID_TELEGRAM_SENDER", "Telegram sender (from.id) is required", 422)

        from_user_id = int(from_user["id"])
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        chat_id = int(chat.get("id") or from_user_id)

        text_body = str(message.get("text") or "").strip()
        contact = message.get("contact")

        # 1. Handle /start or /start <challenge_id>
        if text_body.startswith("/start"):
            parts = text_body.split(maxsplit=1)
            arg_challenge_id = parts[1].strip() if len(parts) > 1 else None
            bound_challenge_id = explicit_challenge_id or arg_challenge_id

            if bound_challenge_id:
                save_domain_record(
                    TELEGRAM_SESSION_NAMESPACE,
                    str(from_user_id),
                    {
                        "challenge_id": bound_challenge_id,
                        "chat_id": chat_id,
                        "started_at": now().isoformat(),
                    },
                )

            reply_markup = {
                "keyboard": [[{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]],
                "resize_keyboard": True,
                "one_time_keyboard": True,
            }
            bot_msg = (
                "Assalomu alaykum! FlexBridge platformasida telefon raqamingizni tasdiqlash uchun "
                "pastdagi «📱 Telefon raqamni yuborish» maxsus tugmasini bosing.\n\n"
                "Diqqat: Telegram hisobingizdagi telefon raqam saytda kiritilgan raqamga "
                "to‘liq mos kelishi shart."
            )
            _send_telegram_api_message(chat_id, bot_msg, reply_markup)
            return {
                "ok": True,
                "step": "AWAITING_CONTACT",
                "bound_challenge_id": bound_challenge_id,
                "telegram_user_id": from_user_id,
                "bot_message": bot_msg,
                "reply_markup": reply_markup,
            }

        # 2. If user sent plain text instead of native Telegram contact button
        if contact is None:
            err_msg = (
                "Raqamni qo‘lda yozib yubormang! Bot raqam haqiqatan sizga tegishli ekanini "
                "tekshirishi uchun pastdagi «📱 Telefon raqamni yuborish» maxsus tugmasini bosing."
            )
            _send_telegram_api_message(
                chat_id,
                err_msg,
                {
                    "keyboard": [[{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True,
                },
            )
            raise AuthError("TELEGRAM_NATIVE_CONTACT_REQUIRED", err_msg, 422)

        if not isinstance(contact, dict):
            raise AuthError("TELEGRAM_NATIVE_CONTACT_REQUIRED", "Valid Telegram contact object is required", 422)

        # 3. Verify contact ownership (anti-spoofing: contact.user_id must match message.from.id)
        contact_user_id = contact.get("user_id")
        if contact_user_id is None or int(contact_user_id) != from_user_id:
            err_msg = (
                "Xatolik: Yuborilgan kontakt sizning shaxsiy Telegram hisobingizga tegishli emas! "
                "Faqat o‘z raqamingizni «📱 Telefon raqamni yuborish» tugmasi orqali ulashing."
            )
            _send_telegram_api_message(chat_id, err_msg)
            raise AuthError("TELEGRAM_CONTACT_OWNERSHIP_MISMATCH", err_msg, 403)

        # 4. Normalize Telegram contact phone number
        telegram_phone = _normalize_telegram_phone(str(contact.get("phone_number") or ""))

        # 5. Resolve target challenge & verify website phone matches Telegram phone
        target_challenge_id = explicit_challenge_id
        if not target_challenge_id:
            sess = load_domain_record(TELEGRAM_SESSION_NAMESPACE, str(from_user_id))
            if isinstance(sess, dict) and sess.get("challenge_id"):
                target_challenge_id = str(sess["challenge_id"])

        t = table("auth_challenges")
        with transaction() as conn:
            row = None
            if target_challenge_id:
                row = (
                    conn.execute(select(t).where(t.c.id == str(target_challenge_id)).with_for_update())
                    .mappings()
                    .first()
                )
                if not row or row["consumed_at"] or row["superseded_at"] or row["expires_at"] <= now():
                    raise AuthError(
                        "INVALID_OR_EXPIRED_CHALLENGE",
                        "Tasdiqlash so‘rovi topilmadi yoki muddati tugagan. Saytdan qaytadan so‘rov yuboring.",
                        404,
                    )
            else:
                dest_digest = digest("destination", "PHONE:" + telegram_phone)
                row = (
                    conn.execute(
                        select(t)
                        .where(
                            t.c.destination_digest == dest_digest,
                            t.c.consumed_at.is_(None),
                            t.c.superseded_at.is_(None),
                            t.c.expires_at > now(),
                        )
                        .order_by(t.c.created_at.desc())
                        .limit(1)
                        .with_for_update()
                    )
                    .mappings()
                    .first()
                )
                if not row:
                    err_msg = (
                        f"Saytda {telegram_phone} raqami uchun faol Telegram tasdiqlash so‘rovi topilmadi. "
                        "Avval saytda shu raqamni kiritib «Telegram orqali olish» tugmasini bosing."
                    )
                    _send_telegram_api_message(chat_id, err_msg)
                    raise AuthError("NO_MATCHING_WEBSITE_CHALLENGE", err_msg, 404)

            dest_data = decrypt(row["destination_encrypted"])
            if dest_data.get("delivery_method") != "TELEGRAM":
                raise AuthError(
                    "INVALID_DELIVERY_METHOD",
                    "Ushbu tasdiqlash so‘rovi Telegram orqali olish uchun yaratilmagan.",
                    422,
                )

            website_phone = dest_data.get("value")
            if website_phone != telegram_phone:
                err_msg = (
                    f"Xatolik: Saytda kiritilgan telefon raqami ({website_phone}) Telegram botda "
                    f"yuborilgan raqamingizga ({telegram_phone}) mos kelmadi! "
                    "Ro‘yxatdan o‘tish uchun saytda aynan o‘z Telegram raqamingizni kiriting."
                )
                _send_telegram_api_message(chat_id, err_msg)
                raise AuthError("TELEGRAM_PHONE_MISMATCH", err_msg, 409)

            if not row["delivery_encrypted"]:
                raise AuthError("INVALID_OR_EXPIRED_CODE", "Tasdiqlash kodi allaqachon ishlatilgan.", 409)

            deliv_data = decrypt(row["delivery_encrypted"])
            otp_code = deliv_data["code"]

            updated_dest = {
                **dest_data,
                "telegram_verified": True,
                "telegram_user_id": from_user_id,
                "telegram_chat_id": chat_id,
                "telegram_verified_at": now().isoformat(),
            }
            conn.execute(
                t.update()
                .where(t.c.id == row["id"])
                .values(
                    delivery_status="SENT",
                    sent_at=now(),
                    destination_encrypted=encrypt(updated_dest),
                    updated_at=now(),
                )
            )
            audit.append_audit_event(
                actor_id=row["user_id"],
                action="TELEGRAM_CONTACT_VERIFIED_OTP_SENT",
                entity_type="auth_challenge",
                entity_id=str(row["id"]),
                metadata={
                    "telegram_user_id": from_user_id,
                    "destination_digest": row["destination_digest"],
                },
            )
            challenge_id_str = str(row["id"])

        bot_msg = (
            f"✅ Telefon raqamingiz ({telegram_phone}) saytda kiritilgan raqam bilan mos keldi va tasdiqlandi!\n\n"
            f"🔐 Sizning tasdiqlash kodingiz: {otp_code}\n\n"
            "Ushbu 6 xonali kodni FlexBridge saytidagi tasdiqlash oynasiga kiriting (amal qilish muddati: 5 daqiqa)."
        )
        remove_kb = {"remove_keyboard": True}
        _send_telegram_api_message(chat_id, bot_msg, remove_kb)

        return {
            "ok": True,
            "step": "CONTACT_VERIFIED_OTP_DELIVERED",
            "challenge_id": challenge_id_str,
            "verified_phone": telegram_phone,
            "telegram_verified": True,
            "delivery_status": "SENT",
            "otp_code": otp_code,
            "bot_message": bot_msg,
            "reply_markup": remove_kb,
        }


telegram_bot_service = TelegramBotVerificationService()
