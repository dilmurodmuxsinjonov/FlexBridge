import { NextResponse } from "next/server";
import { proxyAuthed } from "@/lib/server/proxy";

/** POST /api/bff/moderation-cases (`API-007`: report abuse on listing/org/rating/file) */
export async function POST(request: Request) {
  let body: Record<string, unknown>;
  try {
    const raw = await request.json();
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
    }
    body = raw as Record<string, unknown>;
  } catch {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }

  return proxyAuthed(request, "/api/v1/moderation-cases", {
    method: "POST",
    body,
    fallbackError: "MODERATION_REPORT_FAILED",
  });
}
