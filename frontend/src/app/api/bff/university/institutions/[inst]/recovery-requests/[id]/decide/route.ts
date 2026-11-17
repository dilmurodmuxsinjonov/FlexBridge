import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST — coordinator vouches for (APPROVE) or rejects a student's recovery request. */
export async function POST(request: Request, context: { params: Promise<{ inst: string; id: string }> }) {
  const { inst, id } = await context.params;
  if (!UUID_RE.test(inst) || !UUID_RE.test(id)) return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const decision = body.decision === "APPROVE" ? "APPROVE" : body.decision === "REJECT" ? "REJECT" : null;
  if (!decision) return NextResponse.json({ ok: false, error: "INVALID_DECISION" }, { status: 400 });
  return proxyAuthed(request, `/api/v1/institutions/${inst}/recovery-requests/${id}/decide`, {
    method: "POST",
    body: { decision, reason: String(body.reason || "").trim() },
    fallbackError: "RECOVERY_DECISION_FAILED",
  });
}
