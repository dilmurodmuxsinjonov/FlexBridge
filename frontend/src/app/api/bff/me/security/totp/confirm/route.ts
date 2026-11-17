import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/me/security/totp/confirm
 * Validates 6-digit TOTP code, enables TOTP credential, and rotates security version.
 */
export async function POST(request: NextRequest) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json(
        { ok: false, error: "CSRF_DETECTED", message: "Xavfsizlik tekshiruvidan o'tmadi (Origin header mos kelmadi)." },
        { status: 403 }
      );
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "TOTP kodini tasdiqlash uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const { code } = body;

    if (!code || typeof code !== "string" || !/^[0-9]{6}$/.test(code.trim())) {
      return NextResponse.json(
        { ok: false, error: "INVALID_TOTP_CODE", message: "6 xonali raqamli TOTP kodi kiritilishi shart." },
        { status: 400 }
      );
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/me/security/totp/confirm`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ code: code.trim() }),
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "TOTP_CONFIRMATION_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-060-CONFIRM",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
