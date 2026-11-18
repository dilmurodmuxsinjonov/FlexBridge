import { NextResponse } from "next/server";
import { proxyAuthed, proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** GET & POST /api/bff/candidate/log-entries/[id]/evidence (`API-055`) */
export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_TASK_ENTRY_ID" }, { status: 400 });
  }
  return proxyAuthed(request, `/api/v1/log-entries/${id}/evidence`, {
    method: "GET",
    fallbackError: "LOG_EVIDENCE_LIST_FAILED",
  });
}

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_TASK_ENTRY_ID" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/log-entries/${id}/evidence`, "POST", "LOG_EVIDENCE_ATTACH_FAILED");
}
