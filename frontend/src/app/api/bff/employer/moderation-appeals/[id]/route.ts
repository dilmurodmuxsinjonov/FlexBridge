import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/employer/moderation-appeals/[id] */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_APPEAL_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/moderation-appeals/${encodeURIComponent(id)}`, {
    method: "GET",
    fallbackError: "MODERATION_APPEAL_FETCH_FAILED",
  });
}
