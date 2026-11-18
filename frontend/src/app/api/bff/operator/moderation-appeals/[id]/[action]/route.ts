import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/**
 * POST claims or decides an opportunity rejection appeal (MODERATOR + MFA).
 * Backend FastAPI routes under moderation_appeals.py expose:
 * - POST /api/v1/operator/moderation-cases/{id}/claim
 * - POST /api/v1/operator/moderation-cases/{id}/actions
 */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string; action: string }> }
) {
  const { id, action } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }
  if (action !== "claim" && action !== "decide") {
    return NextResponse.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  }
  if (action === "claim") {
    return proxyAuthed(request, `/api/v1/operator/moderation-cases/${id}/claim`, {
      method: "POST",
      body: {},
      fallbackError: "APPEAL_CLAIM_FAILED",
    });
  }
  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, `/api/v1/operator/moderation-cases/${id}/actions`, {
    method: "POST",
    body,
    fallbackError: "APPEAL_DECIDE_FAILED",
  });
}
