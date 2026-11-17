import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST approves or rejects a pending account recovery request (ADMIN / SUPPORT + MFA). */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }
  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, `/api/v1/operator/recovery-requests/${id}/decide`, {
    method: "POST",
    body,
    fallbackError: "RECOVERY_DECISION_FAILED",
  });
}
