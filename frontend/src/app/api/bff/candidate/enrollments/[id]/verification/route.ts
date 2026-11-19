import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/candidate/enrollments/[id]/verification */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_ENROLLMENT_ID" }, { status: 400 });
  }
  return proxyJsonBody(
    request,
    `/api/v1/me/enrollments/${encodeURIComponent(id)}/verification`,
    "POST",
    "ENROLLMENT_VERIFICATION_FAILED"
  );
}
