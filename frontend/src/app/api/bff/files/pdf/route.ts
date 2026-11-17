import { NextResponse } from "next/server";
import { proxyAuthed } from "@/lib/server/proxy";

const PURPOSES = new Set(["INSTITUTION_APPOINTMENT", "INSTITUTION_AGREEMENT", "ORGANIZATION_EVIDENCE"]);

/** POST /api/bff/files/pdf — staff evidence PDF (scanned fail-closed by the backend). */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const purpose = String(body.purpose || "");
  if (!PURPOSES.has(purpose)) {
    return NextResponse.json({ ok: false, error: "INVALID_FILE_PURPOSE" }, { status: 400 });
  }
  return proxyAuthed(request, "/api/v1/files/pdf", {
    method: "POST",
    body: { filename: String(body.filename || "document.pdf").slice(0, 240), purpose, content_base64: String(body.content_base64 || "") },
    fallbackError: "FILE_UPLOAD_FAILED",
  });
}
