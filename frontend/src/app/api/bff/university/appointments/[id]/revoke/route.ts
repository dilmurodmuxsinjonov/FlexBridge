import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/university/appointments/[id]/revoke — end a staff appointment (reason >= 15 chars). */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) return NextResponse.json({ ok: false, error: "INVALID_APPOINTMENT_ID" }, { status: 400 });
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  return proxyAuthed(request, `/api/v1/institution-appointments/${id}/revoke`, {
    method: "POST",
    body: { reason: String(body.reason || "").trim() },
    fallbackError: "APPOINTMENT_REVOKE_FAILED",
  });
}
