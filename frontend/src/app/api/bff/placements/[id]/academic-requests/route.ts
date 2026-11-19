import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/placements/[id]/academic-requests */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/placements/${id}/academic-requests`, "POST", "ACADEMIC_REQUEST_FAILED");
}
