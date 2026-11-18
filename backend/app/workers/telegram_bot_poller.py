"""Real Telegram bot runner for phone verification.

Two ways to receive Telegram updates:

* Polling (this worker, default): calls Bot API getUpdates in a loop. Works on a
  laptop or private server with no public HTTPS URL. Start it with
  ``python -m app.workers.telegram_bot_poller``.
* Webhook (public HTTPS): ``python -m app.workers.telegram_bot_poller --set-webhook
  https://<site>/api/bff/auth/telegram/webhook`` registers the URL with
  TELEGRAM_WEBHOOK_SECRET as Telegram's secret_token. Telegram then calls the
  webhook and getUpdates is no longer used.

Required: TELEGRAM_BOT_TOKEN (from @BotFather). Optional: TELEGRAM_BOT_USERNAME
(resolved with getMe and logged if unset), TELEGRAM_WEBHOOK_SECRET (webhook mode),
TELEGRAM_API_BASE_URL (tests). Without a token the worker idles so the stack can
always include it.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Any, Callable

import httpx

logger = logging.getLogger("telegram_bot_poller")

POLL_TIMEOUT_SECONDS = 25
IDLE_SLEEP_SECONDS = 300
MAX_BACKOFF_SECONDS = 60


def _api_base() -> str:
    return os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip("/")


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def call_api(client: httpx.Client, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post(f"{_api_base()}/bot{_token()}/{method}", json=payload or {})
    data = response.json()
    if not data.get("ok"):
        # Never log the URL: it contains the bot token.
        raise RuntimeError(f"Telegram {method} failed: {data.get('error_code')} {data.get('description')}")
    return data


def process_update(update: dict[str, Any], handler: Callable[..., dict[str, Any]] | None = None) -> str:
    """Feed one Telegram update to the verification service. Returns a short outcome code.

    The service itself messages the user on every outcome (prompt, mismatch, code),
    so errors here are expected user mistakes, not worker failures.
    """
    from app.services.auth import AuthError

    if handler is None:
        from app.services.telegram_bot import telegram_bot_service
        handler = telegram_bot_service.handle_update
    message = update.get("message")
    if not isinstance(message, dict):
        return "IGNORED"
    sender = (message.get("from") or {}).get("id")
    try:
        result = handler(update=update, ip=f"tg:{sender}" if sender else "telegram-poll")
    except AuthError as exc:
        return exc.code
    return str(result.get("step") or "OK")


def poll_forever(client: httpx.Client, stop_after: int | None = None) -> None:
    """Long-poll getUpdates. `stop_after` bounds iterations for tests."""
    offset: int | None = None
    backoff = 1
    iterations = 0
    while stop_after is None or iterations < stop_after:
        iterations += 1
        try:
            payload: dict[str, Any] = {"timeout": POLL_TIMEOUT_SECONDS, "allowed_updates": ["message"]}
            if offset is not None:
                payload["offset"] = offset
            updates = call_api(client, "getUpdates", payload).get("result", [])
            backoff = 1
        except Exception as exc:  # network / Telegram outage: retry with backoff
            logger.warning("getUpdates failed (%s); retrying in %ss", type(exc).__name__, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
            continue
        for update in updates:
            offset = int(update["update_id"]) + 1
            outcome = process_update(update)
            logger.info("update %s -> %s", update.get("update_id"), outcome)


def set_webhook(client: httpx.Client, url: str) -> None:
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if len(secret) < 16:
        raise SystemExit("Set TELEGRAM_WEBHOOK_SECRET (16+ chars, A-Z a-z 0-9 _ -) before registering a webhook.")
    call_api(client, "setWebhook", {"url": url, "secret_token": secret, "allowed_updates": ["message"]})
    logger.info("Webhook registered: %s", url)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    # Never log httpx/httpcore request URLs because Telegram Bot API paths embed the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set-webhook", metavar="URL", help="register a webhook instead of polling")
    parser.add_argument("--delete-webhook", action="store_true", help="remove the webhook and exit")
    args = parser.parse_args(argv)

    if not _token():
        logger.info("TELEGRAM_BOT_TOKEN is not set; Telegram bot is idle (SMS remains available).")
        if args.set_webhook or args.delete_webhook:
            return 2
        while True:
            time.sleep(IDLE_SLEEP_SECONDS)

    with httpx.Client(timeout=POLL_TIMEOUT_SECONDS + 10, follow_redirects=False) as client:
        me = call_api(client, "getMe").get("result", {})
        username = me.get("username")
        configured = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")
        logger.info("Connected as @%s", username)
        if username and configured and configured.lower() != str(username).lower():
            logger.warning("TELEGRAM_BOT_USERNAME=%s differs from the token's bot @%s; deep links will be wrong.", configured, username)
        if args.set_webhook:
            set_webhook(client, args.set_webhook)
            return 0
        # getUpdates and webhooks are mutually exclusive in the Bot API.
        call_api(client, "deleteWebhook", {"drop_pending_updates": False})
        if args.delete_webhook:
            logger.info("Webhook deleted.")
            return 0
        poll_forever(client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
