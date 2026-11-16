import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

/** PUT /api/bff/candidate/visibility — student consent to appear in employer search. */
export async function PUT(request: Request) {
  if (!verifyCsrfOrigin(request)) return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  const session = await getSessionFromCookie();
  if (!session?.access_token) return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  const body = await request.json().catch(() => ({}));
  try {
    const res = await backendFetch(
      "/api/v1/me/candidate/visibility",
      { method: "PUT", body: JSON.stringify({ visibility: body.visibility }), headers: { "Content-Type": "application/json" } },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json({ ok: false, error: data.detail?.code || "VISIBILITY_UPDATE_FAILED" }, { status: res.status });
    return NextResponse.json({ ok: true, visibility: data.visibility });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR" }, { status: 502 });
  }
}
