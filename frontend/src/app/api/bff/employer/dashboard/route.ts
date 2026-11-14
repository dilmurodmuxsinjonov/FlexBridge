import { NextResponse } from "next/server";
import { backendFetch, getSession } from "@/lib/server/session";

export async function GET(request: Request) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const org = searchParams.get("org");

  if (!org) {
    return NextResponse.json(
      { ok: false, error: "ORGANIZATION_ID_REQUIRED" },
      { status: 400 }
    );
  }

  // Basic UUID format guard
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(org)) {
    return NextResponse.json(
      { ok: false, error: "INVALID_ORGANIZATION_ID" },
      { status: 400 }
    );
  }

  try {
    const backendRes = await backendFetch(
      `/api/v1/organizations/${encodeURIComponent(org)}/dashboard`,
      { method: "GET" },
      session.token
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorMessage =
        typeof data.detail === "object" && data.detail?.message
          ? data.detail.message
          : typeof data.detail === "string"
          ? data.detail
          : "REQUEST_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: data.contract_id || "API-068",
      organization_id: data.organization_id || org,
      opportunities: data.opportunities,
      applications: data.applications,
      engagements: data.engagements,
      interviews: data.interviews,
      metrics: {
        opportunities: data.opportunities,
        applications: data.applications,
        engagements: data.engagements,
        interviews: data.interviews,
      },
    });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
