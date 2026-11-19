import { NextResponse } from "next/server";
import { proxyAuthed } from "@/lib/server/proxy";

const ALLOWED_STAGES = new Set(["MODERATOR", "COMPLIANCE"]);

/** GET organization owner-continuity cases for MODERATOR or COMPLIANCE stage. */
export async function GET(
  request: Request,
  context: { params: Promise<{ stage: string }> }
) {
  const { stage } = await context.params;
  const upper = (stage || "").toUpperCase();
  if (!ALLOWED_STAGES.has(upper)) {
    return NextResponse.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  }
  const incoming = new URL(request.url).searchParams;
  const qs = new URLSearchParams();
  for (const key of ["unassigned", "limit"] as const) {
    const val = incoming.get(key);
    if (val !== null && val.trim() && val.length <= 32) {
      qs.set(key, val.trim());
    }
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return proxyAuthed(request, `/api/v1/operator/owner-continuity/${upper.toLowerCase()}/cases${suffix}`, {
    method: "GET",
    fallbackError: "OWNER_CONTINUITY_FETCH_FAILED",
  });
}
