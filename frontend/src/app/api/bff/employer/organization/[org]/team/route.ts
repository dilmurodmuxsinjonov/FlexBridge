import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET — owner (main account) view of members, join requests and open invitations. */
export async function GET(request: Request, context: { params: Promise<{ org: string }> }) {
  const { org } = await context.params;
  if (!UUID_RE.test(org)) return NextResponse.json({ ok: false, error: "INVALID_ORG_ID" }, { status: 400 });
  return proxyAuthed(request, `/api/v1/organizations/${org}/team`, { method: "GET", fallbackError: "TEAM_FETCH_FAILED" });
}
