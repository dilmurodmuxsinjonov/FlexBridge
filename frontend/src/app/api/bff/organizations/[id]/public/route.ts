import { NextResponse } from "next/server";
import { proxyPublic, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/organizations/[id]/public (`API-008`) */
export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyPublic(`/api/v1/organizations/${id}/public`, "ORGANIZATION_NOT_FOUND");
}
