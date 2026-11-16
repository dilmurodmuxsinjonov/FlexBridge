import { NextResponse } from "next/server";
import { verifyCsrfOrigin } from "@/lib/server/session";
import { forwardRecovery } from "./_proxy";

/** POST /api/bff/auth/recovery — verified RECOVERY OTP proof + optional TOTP / backup code. */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }
  const body = await request.json().catch(() => ({}));
  const payload: Record<string, string> = { verification_token: String(body?.verification_token || "") };
  if (body?.totp_code) payload.totp_code = String(body.totp_code).trim();
  if (body?.recovery_code) payload.recovery_code = String(body.recovery_code).trim();
  return forwardRecovery("/auth/recovery", { method: "POST", body: payload });
}
