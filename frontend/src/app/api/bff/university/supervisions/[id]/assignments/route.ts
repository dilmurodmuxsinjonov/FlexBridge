import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/university/supervisions/[id]/assignments */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_SUPERVISION_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/student-supervisions/${id}/academic-assignments`, {
    method: "GET",
    fallbackError: "SUPERVISION_ASSIGNMENTS_FETCH_FAILED",
  });
}
