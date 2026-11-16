import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** GET /api/bff/university/institutions/[inst]/staff — coordinator staff list + current agreement. */
export async function GET(request: Request, context: { params: Promise<{ inst: string }> }) {
  const { inst } = await context.params;
  if (!UUID_RE.test(inst)) return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
  return proxyAuthed(request, `/api/v1/institutions/${inst}/staff-appointments`, { method: "GET", fallbackError: "STAFF_FETCH_FAILED" });
}
