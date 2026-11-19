import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/files/[id]/download (`API-X03`) */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_FILE_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/files/${id}/download`, {
    method: "GET",
    fallbackError: "FILE_DOWNLOAD_FAILED",
  });
}
