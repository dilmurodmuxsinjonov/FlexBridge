import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** PUT /api/bff/employer/opportunities/[id]/draft/schedule (`API-080`) */
export async function PUT(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_OPPORTUNITY_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/opportunities/${id}/draft/schedule`, "PUT", "DRAFT_SCHEDULE_UPDATE_FAILED");
}
