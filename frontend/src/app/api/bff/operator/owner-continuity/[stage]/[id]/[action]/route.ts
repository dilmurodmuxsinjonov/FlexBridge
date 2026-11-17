import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

const ALLOWED_STAGES = new Set(["MODERATOR", "COMPLIANCE"]);
const ALLOWED_ACTIONS = new Set(["claim", "decide"]);

/** POST claims or decides an organization owner-continuity case at MODERATOR or COMPLIANCE stage. */
export async function POST(
  request: Request,
  context: { params: Promise<{ stage: string; id: string; action: string }> }
) {
  const { stage, id, action } = await context.params;
  const upperStage = (stage || "").toUpperCase();
  if (!ALLOWED_STAGES.has(upperStage) || !ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  }
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }
  const body = action === "claim" ? {} : await request.json().catch(() => ({}));
  return proxyAuthed(
    request,
    `/api/v1/operator/owner-continuity/${upperStage.toLowerCase()}/cases/${id}/${action}`,
    {
      method: "POST",
      body,
      fallbackError: action === "claim" ? "CONTINUITY_CLAIM_FAILED" : "CONTINUITY_DECIDE_FAILED",
    }
  );
}
