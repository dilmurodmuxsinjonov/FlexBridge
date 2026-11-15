import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/me/security/recovery-codes
 * Generates 8 one-time backup recovery codes with password & MFA step-up verification.
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
        { ok: false, error: "AUTH_REQUIRED", message: "Zaxira kodlarini yaratish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const { current_password, totp_code } = body;

    if (!current_password || typeof current_password !== "string" || current_password.trim() === "") {
      return NextResponse.json(
        { ok: false, error: "STEP_UP_VERIFICATION_FAILED", message: "Joriy maxfiy so'z (parol) kiritilishi shart." },
        { status: 400 }
      );
    }

    const payload: Record<string, unknown> = {
      current_password: current_password.trim(),
    };
    if (totp_code && typeof totp_code === "string") {
      payload.totp_code = totp_code.trim();
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/me/security/recovery-codes`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "RECOVERY_CODES_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-060-RECOVERY",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
