import { NextResponse } from "next/server";
import { proxyAuthed, proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** GET & POST /api/bff/employer/placements/[id]/mentor-assignments (`API-087`) */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/placements/${id}/mentor-assignments`, {
    method: "GET",
    fallbackError: "MENTOR_ASSIGNMENTS_FETCH_FAILED",
  });
}

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/placements/${id}/mentor-assignments`, "POST", "MENTOR_NOMINATION_FAILED");
}
