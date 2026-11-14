import { NextResponse } from "next/server";
import { backendFetch, clearSessionCookie, getSession } from "@/lib/server/session";

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ ok: false, error: "UNAUTHENTICATED" }, { status: 401 });
  }

  try {
    const backendRes = await backendFetch("/api/v1/auth/me", { method: "GET" }, session.token);

    if (!backendRes.ok) {
      await clearSessionCookie();
      return NextResponse.json({ ok: false, error: "SESSION_EXPIRED" }, { status: 401 });
    }

    const data = await backendRes.json();
    return NextResponse.json({
      ok: true,
      user: {
        user_id: data.user_id,
        session_id: data.session_id,
        roles: data.roles || session.roles,
      },
    });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
