import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/placements/[id]/plan — role-neutral read for mentor/teacher acceptance */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/placements/${id}/plan`, {
    method: "GET",
    fallbackError: "PLACEMENT_PLAN_FETCH_FAILED",
  });
}
