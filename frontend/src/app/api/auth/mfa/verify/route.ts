import { NextResponse } from "next/server";
import { backendFetch, setSessionCookie, verifyCsrfOrigin } from "@/lib/server/session";

export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const body = await request.json();
    const { mfa_ticket, code } = body || {};

    if (!mfa_ticket || !code) {
      return NextResponse.json(
        { ok: false, error: "MFA_TICKET_AND_CODE_REQUIRED" },
        { status: 400 }
      );
    }

    const backendRes = await backendFetch("/api/v1/auth/mfa/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mfa_ticket, code }),
    });

    const data = await backendRes.json().catch(() => ({}));
    const token = data.access_token || data.token;

    if (backendRes.ok && token) {
      const expiresIn = typeof data.expires_in === "number" ? data.expires_in : 43200;

      let resolvedUserId = "";
      let resolvedRoles: string[] = [];

      try {
        const meRes = await backendFetch("/api/v1/auth/me", { method: "GET" }, token);
        if (meRes.ok) {
          const meData = await meRes.json();
          resolvedUserId = String(meData.user_id || "");
          resolvedRoles = Array.isArray(meData.roles) ? meData.roles : [];
        }
      } catch {
        // Fallback
      }

      await setSessionCookie({
        token: token,
        user_id: resolvedUserId,
        roles: resolvedRoles,
        expires_at: Math.floor(Date.now() / 1000) + expiresIn,
      });

      return NextResponse.json({
        ok: true,
        user_id: resolvedUserId,
        roles: resolvedRoles,
      });
    }

    const errorMessage =
      typeof data.detail === "object" && data.detail?.message
        ? data.detail.message
        : typeof data.detail === "string"
        ? data.detail
        : "MFA_VERIFICATION_FAILED";

    return NextResponse.json(
      { ok: false, error: errorMessage },
      { status: backendRes.status || 401 }
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
