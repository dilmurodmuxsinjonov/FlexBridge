import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * DELETE /api/bff/me/sessions/[id] (API-061)
 * Revokes an active session owned by the authenticated user.
 */
export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
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
        { ok: false, error: "AUTH_REQUIRED", message: "Sessiyani bekor qilish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { id: sessionId } = await context.params;
    if (!sessionId) {
      return NextResponse.json(
        { ok: false, error: "MISSING_SESSION_ID", message: "Sessiya identifikatori kiritilishi shart." },
        { status: 400 }
      );
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/me/sessions/${sessionId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "REVOKE_SESSION_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    const response = NextResponse.json({
      ok: true,
      contract_id: "API-061",
      ...data,
    });

    // If the user revoked their current active session, clear the session cookie
    if (session.session_id && session.session_id === sessionId) {
      response.cookies.delete("flexbridge_session");
    }

    return response;
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
