import { NextResponse } from "next/server";
import { proxyAuthed, proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** GET / POST /api/bff/employer/organization/[org]/owner-continuity */
export async function GET(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/organizations/${org}/owner-continuity`, {
    method: "GET",
    fallbackError: "OWNER_CONTINUITY_LIST_FAILED",
  });
}

export async function POST(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) {
    return NextResponse.json({ ok: false, error: "INVALID_ORGANIZATION_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/organizations/${org}/owner-continuity`, "POST", "OWNER_CONTINUITY_SUBMIT_FAILED", true);
}
