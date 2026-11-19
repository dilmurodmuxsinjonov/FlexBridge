import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST revokes an active platform role grant (ADMIN + MFA required). */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }
  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, `/api/v1/operator/staff-grants/${id}/revoke`, {
    method: "POST",
    body,
    fallbackError: "STAFF_REVOKE_FAILED",
  });
}
