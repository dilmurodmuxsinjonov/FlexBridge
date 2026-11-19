import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/placements/[id]/assignments/[assignment]/accept (`API-051`) */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string; assignment: string }> }
) {
  const { id, assignment } = await context.params;
  if (!UUID_RE.test(id) || !UUID_RE.test(assignment)) {
    return NextResponse.json({ ok: false, error: "INVALID_IDENTIFIER" }, { status: 400 });
  }
  return proxyJsonBody(
    request,
    `/api/v1/placements/${id}/assignments/${assignment}/accept`,
    "POST",
    "ASSIGNMENT_ACCEPT_FAILED"
  );
}
