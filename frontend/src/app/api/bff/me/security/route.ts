import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * GET /api/bff/me/security
 * Returns TOTP status, recovery codes count, current session ID, and active sessions list.
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Xavfsizlik ma'lumotlarini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/me/security`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "FETCH_SECURITY_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-060-VIEW",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}

/**
 * PATCH /api/bff/me/security (API-060)
 * Step-up password verification, TOTP enrollment/disable under CAP-002 / AUTH_SELF.
 */
export async function PATCH(request: NextRequest) {
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
        { ok: false, error: "AUTH_REQUIRED", message: "Xavfsizlik sozlamalarini o'zgartirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const { enable_totp, current_password, step_up_totp_code } = body;

    if (current_password === undefined || current_password === null || typeof current_password !== "string" || current_password.trim() === "") {
      return NextResponse.json(
        { ok: false, error: "STEP_UP_VERIFICATION_FAILED", message: "Joriy maxfiy so'z (parol) kiritilishi shart." },
        { status: 400 }
      );
    }

    const payload: Record<string, unknown> = {
      enable_totp: Boolean(enable_totp),
      current_password: current_password.trim(),
    };
    if (step_up_totp_code && typeof step_up_totp_code === "string") {
      payload.step_up_totp_code = step_up_totp_code.trim();
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/me/security`, {
      method: "PATCH",
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
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "SECURITY_UPDATE_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-060",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
