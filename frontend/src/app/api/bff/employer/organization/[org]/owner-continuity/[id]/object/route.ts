import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/employer/organization/[org]/owner-continuity/[id]/object */
export async function POST(
  request: Request,
  context: { params: Promise<{ org: string; id: string }> }
) {
  const { org, id } = await context.params;
  if (!UUID_RE.test(org) || !UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_IDENTIFIER" }, { status: 400 });
  }
  return proxyJsonBody(
    request,
    `/api/v1/organizations/${org}/owner-continuity/${id}/object`,
    "POST",
    "OWNER_CONTINUITY_OBJECT_FAILED"
  );
}
