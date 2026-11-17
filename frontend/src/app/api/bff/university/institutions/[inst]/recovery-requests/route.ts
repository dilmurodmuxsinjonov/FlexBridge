import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET — coordinator queue of students' password-recovery requests. */
export async function GET(request: Request, context: { params: Promise<{ inst: string }> }) {
  const { inst } = await context.params;
  if (!UUID_RE.test(inst)) return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
  return proxyAuthed(request, `/api/v1/institutions/${inst}/recovery-requests`, { method: "GET", fallbackError: "RECOVERY_QUEUE_FAILED" });
}
