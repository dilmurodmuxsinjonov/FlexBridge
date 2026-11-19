import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/university/academic-assignments/[id]/revoke */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_ASSIGNMENT_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/academic-assignments/${id}/revoke`, "POST", "ACADEMIC_REVOKE_FAILED");
}
