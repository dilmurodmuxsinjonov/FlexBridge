import { NextResponse } from "next/server";
import { backendFetch, verifyCsrfOrigin } from "@/lib/server/session";
import { backendErrorCode, readJsonObject } from "@/lib/server/proxy";

/** POST /api/auth/passkeys/options */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const raw = await readJsonObject(request);
  const payload: Record<string, unknown> = {};
  if (typeof raw?.mfa_ticket === "string" && raw.mfa_ticket.trim()) {
    payload.mfa_ticket = raw.mfa_ticket.trim();
  }

  try {
    const res = await backendFetch("/api/v1/auth/passkeys/options", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: backendErrorCode(res.status, data, "PASSKEY_OPTIONS_FAILED") },
        { status: res.status }
      );
    }
    return NextResponse.json({ ok: true, ...data }, { status: 200, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
