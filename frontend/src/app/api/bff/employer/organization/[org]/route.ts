import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** PATCH /api/bff/employer/organization/[org] (`API-071`: audited organization profile edit) */
export async function PATCH(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/organizations/${org}`, "PATCH", "ORGANIZATION_UPDATE_FAILED");
}
