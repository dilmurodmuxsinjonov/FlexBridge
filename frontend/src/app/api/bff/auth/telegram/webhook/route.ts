import { NextResponse } from "next/server";
import { verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/auth/telegram/webhook
 * Proxies Telegram Bot updates (/start and contact sharing) to canonical backend service.
 */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const body = await request.json();

    // Telegram calls this URL with the setWebhook secret_token; forward it so the
    // backend can authenticate the update (LIVE mode). Browsers cannot supply it.
    const telegramSecret = request.headers.get("x-telegram-bot-api-secret-token");
    const backendRes = await fetch(`${backendInternalUrl}/api/v1/auth/telegram/webhook`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(telegramSecret ? { "X-Telegram-Bot-Api-Secret-Token": telegramSecret } : {}),
      },
      body: JSON.stringify(body || {}),
    });

    const data = await backendRes.json().catch(() => ({}));
    if (!backendRes.ok) {
      const errMsg =
        typeof data.detail === "object"
          ? data.detail?.message || data.detail?.code
          : data.detail || "TELEGRAM_VERIFICATION_FAILED";
      const errCode =
        typeof data.detail === "object" ? data.detail?.code : "TELEGRAM_VERIFICATION_FAILED";
      return NextResponse.json(
        { ok: false, error: errMsg, code: errCode, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      {
        ok: false,
        error: "INTERNAL_ERROR",
        message: err instanceof Error ? err.message : "Xatolik yuz berdi",
      },
      { status: 500 }
    );
  }
}
