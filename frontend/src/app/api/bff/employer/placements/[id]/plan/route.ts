import { NextResponse } from "next/server";
import { proxyAuthed, proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** GET & PUT /api/bff/employer/placements/[id]/plan (`API-050`) */
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

export async function PUT(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/placements/${id}/plan`, "PUT", "PLACEMENT_PLAN_PUBLISH_FAILED");
}
