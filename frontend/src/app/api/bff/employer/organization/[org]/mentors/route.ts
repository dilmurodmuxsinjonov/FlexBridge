import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/employer/organization/[org]/mentors */
export async function GET(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/organizations/${org}/mentors`, {
    method: "GET",
    fallbackError: "ORG_MENTORS_FETCH_FAILED",
  });
}
