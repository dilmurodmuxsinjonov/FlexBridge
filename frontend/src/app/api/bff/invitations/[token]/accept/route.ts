import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  getSessionFromCookie,
  setSessionCookie,
  verifyCsrfOrigin,
} from "@/lib/server/session";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ token: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Taklifni qabul qilish uchun tizimga kirish shart." },
      { status: 401 }
    );
  }

  const { token } = await context.params;
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) {
    return NextResponse.json(
      { ok: false, error: "INVALID_INVITATION_TOKEN", message: "Taklif tokeni formati noto‘g‘ri." },
      { status: 400 }
    );
  }

  try {
    const res = await backendFetch(
      `/api/v1/invitations/${encodeURIComponent(token)}/accept`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: data?.detail?.code || data?.detail || data?.error || "INVITATION_ACCEPT_FAILED",
          message: "Taklifni qabul qilib bo‘lmadi.",
        },
        { status: res.status }
      );
    }

    let updatedRoles = session.roles;
    const meRes = await backendFetch("/api/v1/auth/me", { method: "GET" }, session.access_token);
    if (meRes.ok) {
      const meData = await meRes.json().catch(() => null);
      if (meData && Array.isArray(meData.roles)) {
        updatedRoles = meData.roles;
        await setSessionCookie({
          token: session.access_token,
          user_id: String(meData.user_id || session.user_id),
          roles: updatedRoles,
          expires_at: session.expires_at,
        });
      }
    }

    return NextResponse.json({ ok: true, ...data, roles: updatedRoles }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR" },
      { status: 500 }
    );
  }
}
