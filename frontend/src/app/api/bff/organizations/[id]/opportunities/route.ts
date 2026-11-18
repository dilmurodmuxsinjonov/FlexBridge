import { NextRequest, NextResponse } from "next/server";
import { proxyPublic, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/organizations/[id]/opportunities (`API-009`) */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  const { searchParams } = new URL(request.url);
  const query = new URLSearchParams();
  const limitRaw = Number(searchParams.get("limit") || "20");
  if (Number.isFinite(limitRaw)) {
    query.set("limit", String(Math.min(Math.max(1, Math.trunc(limitRaw)), 50)));
  }
  const after = searchParams.get("after");
  if (after) query.set("after", after);
  const qs = query.toString();
  return proxyPublic(
    `/api/v1/organizations/${id}/opportunities${qs ? `?${qs}` : ""}`,
    "ORGANIZATION_OPPORTUNITIES_FAILED",
    "public, max-age=30, stale-while-revalidate=60"
  );
}
