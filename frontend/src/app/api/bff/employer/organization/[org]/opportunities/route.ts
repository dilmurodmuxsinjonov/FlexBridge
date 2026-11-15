import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

/**
 * GET /api/bff/employer/organization/[org]/opportunities?status=
 * Every vacancy of the organization (all statuses) for its managers (API-076).
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ org: string }> }) {
  const session = await getSessionFromCookie();
  if (!session?.access_token) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }
  const { org } = await params;
  const status = request.nextUrl.searchParams.get("status");
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  try {
    const res = await backendFetch(
      `/api/v1/organizations/${encodeURIComponent(org)}/opportunities/manage${qs}`,
      { method: "GET" },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json({ ok: false, error: "ORG_OPPORTUNITIES_FAILED", detail: data.detail }, { status: res.status });
    }
    return NextResponse.json({ ok: true, contract_id: "API-076", items: Array.isArray(data.items) ? data.items : [] });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR", message: "Ichki tarmoq xatoligi" }, { status: 502 });
  }
}
