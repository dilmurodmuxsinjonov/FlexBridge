import { NextResponse } from "next/server";
import { backendFetch, clearSessionCookie, getSession, verifyCsrfOrigin } from "@/lib/server/session";

export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSession();
  if (session) {
    try {
      // Best-effort session revocation on backend
      await backendFetch("/api/v1/auth/me", { method: "GET" }, session.token).then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          if (data.session_id) {
            await backendFetch(`/api/v1/me/sessions/${data.session_id}`, { method: "DELETE" }, session.token);
          }
        }
      }).catch(() => {});
    } catch {
      // Ignore network errors during logout
    }
  }

  await clearSessionCookie();
  return NextResponse.json({ ok: true });
}
