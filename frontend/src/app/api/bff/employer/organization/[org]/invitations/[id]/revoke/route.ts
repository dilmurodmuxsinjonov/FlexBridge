import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST — owner cancels an open invitation (reason >= 15 chars). */
export async function POST(request: Request, context: { params: Promise<{ org: string; id: string }> }) {
  const { org, id } = await context.params;
  if (!UUID_RE.test(org) || !UUID_RE.test(id)) return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  return proxyAuthed(request, `/api/v1/organizations/${org}/invitations/${id}/revoke`, {
    method: "POST",
    body: { reason: String(body.reason || "").trim() },
    fallbackError: "INVITATION_REVOKE_FAILED",
  });
}
