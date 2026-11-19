import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";
import { backendErrorCode, readJsonObject, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/matching/preview (`API-003`) */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session?.access_token) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }

  const body = await readJsonObject(request);
  const opportunityId = typeof body?.opportunity_id === "string" ? body.opportunity_id.trim() : "";
  if (opportunityId && !UUID_RE.test(opportunityId)) {
    return NextResponse.json({ ok: false, error: "INVALID_OPPORTUNITY_ID" }, { status: 400 });
  }

  try {
    const profileRes = await backendFetch(
      "/api/v1/me/candidate",
      { method: "GET", headers: { Accept: "application/json" } },
      session.access_token
    );
    const profile = await profileRes.json().catch(() => ({}));
    if (!profileRes.ok || !profile?.id) {
      return NextResponse.json(
        { ok: false, error: backendErrorCode(profileRes.status, profile, "CANDIDATE_PROFILE_REQUIRED") },
        { status: profileRes.status || 403 }
      );
    }

    const payload: Record<string, unknown> = {
      candidate_id: String(profile.id),
      schedule_match_mode:
        body?.schedule_match_mode === "ANY_SHIFT_IN_GROUP" ? "ANY_SHIFT_IN_GROUP" : "ALL_SHIFTS_IN_GROUP",
    };
    if (opportunityId) payload.opportunity_id = opportunityId;
    if (typeof body?.commute_buffer_minutes === "number") {
      payload.commute_buffer_minutes = body.commute_buffer_minutes;
    }

    const res = await backendFetch(
      "/api/v1/matching/preview",
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: backendErrorCode(res.status, data, "MATCHING_PREVIEW_FAILED") },
        { status: res.status }
      );
    }
    return NextResponse.json({ ok: true, ...data }, { status: 200, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
