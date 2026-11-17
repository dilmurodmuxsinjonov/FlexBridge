"""HTTP Caching & Conditional Request Middleware for FlexBridge 1.4 (CAP-039, FIX-HTTP-CACHE).

Provides:
- Standard Cache-Control header constants and route helper functions.
- Automatic strong ETag calculation for public responses.
- Conditional request processing (If-None-Match -> 304 Not Modified).
- Standard security headers (X-Content-Type-Options: nosniff).
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import Response
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


CACHE_CONTROL_PUBLIC_LONG = "public, max-age=600, stale-while-revalidate=120"
CACHE_CONTROL_PUBLIC_MEDIUM = "public, max-age=300, stale-while-revalidate=60"
CACHE_CONTROL_PUBLIC_SHORT = "public, max-age=30, stale-while-revalidate=60"
CACHE_CONTROL_NO_STORE = "no-cache, no-store, must-revalidate"


def apply_public_cache(
    response: Response,
    max_age: int = 300,
    stale_while_revalidate: int = 60,
) -> None:
    """Set standard public cache headers on FastAPI response object."""
    response.headers["Cache-Control"] = (
        f"public, max-age={max_age}, stale-while-revalidate={stale_while_revalidate}"
    )


def apply_no_store(response: Response) -> None:
    """Set strict no-store / no-cache headers on FastAPI response object."""
    response.headers["Cache-Control"] = CACHE_CONTROL_NO_STORE
    response.headers["Pragma"] = "no-cache"


class HTTPCacheMiddleware:
    """ASGI middleware for computing ETag, handling 304 conditional requests, and standardizing headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in ("GET", "HEAD"):
            await self.app(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        if_none_match = request_headers.get("if-none-match")
        initial_message: Message = {}
        response_body = bytearray()

        async def cache_send(message: Message) -> None:
            nonlocal initial_message, response_body
            if message["type"] == "http.response.start":
                initial_message = message
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    headers = MutableHeaders(raw=list(initial_message.get("headers", [])))
                    status_code = initial_message.get("status", 200)

                    # Standard defense-in-depth header
                    if "x-content-type-options" not in headers:
                        headers["x-content-type-options"] = "nosniff"

                    path = scope.get("path", "")
                    if path.startswith("/api/v1/health/"):
                        headers["cache-control"] = CACHE_CONTROL_NO_STORE
                        headers["pragma"] = "no-cache"
                    elif status_code >= 400:
                        # Prevent CDNs and browsers from caching error responses
                        headers["cache-control"] = CACHE_CONTROL_NO_STORE
                        headers["pragma"] = "no-cache"

                    cache_control = headers.get("cache-control", "")
                    if status_code == 200 and "public" in cache_control.lower():
                        digest = hashlib.sha256(response_body).hexdigest()[:16]
                        etag = f'"{digest}"'
                        headers["etag"] = etag
                        if "vary" not in headers:
                            headers["vary"] = "Accept-Encoding"

                        # Handle If-None-Match conditional caching
                        if if_none_match:
                            clean_client_tag = if_none_match.strip()
                            if clean_client_tag in (etag, f"W/{etag}"):
                                headers["content-length"] = "0"
                                await send(
                                    {
                                        "type": "http.response.start",
                                        "status": 304,
                                        "headers": headers.raw,
                                    }
                                )
                                await send(
                                    {
                                        "type": "http.response.body",
                                        "body": b"",
                                        "more_body": False,
                                    }
                                )
                                return

                    await send(
                        {
                            "type": "http.response.start",
                            "status": status_code,
                            "headers": headers.raw,
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": bytes(response_body),
                            "more_body": False,
                        }
                    )

        await self.app(scope, receive, cache_send)
