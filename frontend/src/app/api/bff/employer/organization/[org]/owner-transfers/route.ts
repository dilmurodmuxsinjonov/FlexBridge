import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/employer/organization/[org]/owner-transfers (`ORG_OWNER_TRANSFER`) */
export async function POST(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/organizations/${org}/owner-transfers`, "POST", "OWNER_TRANSFER_FAILED", true);
}
