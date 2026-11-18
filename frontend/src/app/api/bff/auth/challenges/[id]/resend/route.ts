import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";
import { backendErrorCode, readJsonObject, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/auth/challenges/[id]/resend (`API-021`) */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_CHALLENGE_ID" }, { status: 400 });
  }

  const body = await readJsonObject(request);
  const purpose = typeof body?.purpose === "string" ? body.purpose.trim().toUpperCase() : "";
  if (!purpose) {
    return NextResponse.json({ ok: false, error: "MISSING_PURPOSE" }, { status: 400 });
  }

  let token: string | undefined;
  if (purpose === "CONTACT") {
    const session = await getSessionFromCookie();
    if (!session?.access_token) {
      return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
    }
    token = session.access_token;
  }

  try {
    const res = await backendFetch(
      `/api/v1/auth/challenges/${encodeURIComponent(id)}/resend`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ purpose }),
      },
      token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: backendErrorCode(res.status, data, "CHALLENGE_RESEND_FAILED") },
        { status: res.status }
      );
    }
    return NextResponse.json({ ok: true, ...data }, { status: res.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
