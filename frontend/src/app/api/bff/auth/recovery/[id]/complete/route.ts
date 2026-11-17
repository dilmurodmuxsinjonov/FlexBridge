import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfOrigin } from "@/lib/server/session";
import { forwardRecovery } from "../../_proxy";

/** POST /api/bff/auth/recovery/[id]/complete — reset_token + new password (min 12). */
export async function POST(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }
  const { id } = await context.params;
  const body = await request.json().catch(() => ({}));
  const newPassword = String(body?.new_password || "");
  if (newPassword.length < 12) {
    return NextResponse.json({ ok: false, error: "PASSWORD_TOO_SHORT" }, { status: 400 });
  }
  return forwardRecovery(`/auth/recovery/${encodeURIComponent(id)}/complete`, {
    method: "POST",
    body: { reset_token: String(body?.reset_token || ""), new_password: newPassword },
  });
}
