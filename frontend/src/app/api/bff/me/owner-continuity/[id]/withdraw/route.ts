import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/me/owner-continuity/[id]/withdraw */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_CASE_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/owner-continuity/${id}/withdraw`, "POST", "OWNER_CONTINUITY_WITHDRAW_FAILED");
}
