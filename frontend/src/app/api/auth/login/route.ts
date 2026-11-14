import { NextResponse } from "next/server";
import { backendFetch, setSessionCookie, verifyCsrfOrigin } from "@/lib/server/session";

export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const body = await request.json();
    const { destination, password, channel, totp_code } = body || {};

    if (!password || (!destination && !body.user_id)) {
      return NextResponse.json(
        { ok: false, error: "EMAIL_OR_DESTINATION_AND_PASSWORD_REQUIRED" },
        { status: 400 }
      );
    }

    const payload: Record<string, unknown> = {
      password,
      destination: destination || undefined,
      channel: channel || undefined,
      totp_code: totp_code || undefined,
    };
    if (body.user_id) payload.user_id = body.user_id;

    const backendRes = await backendFetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await backendRes.json().catch(() => ({}));

    // Handle 202: MFA Challenge Required (do not set session cookie)
    if (backendRes.status === 202 || data.mfa_required) {
      return NextResponse.json(
        {
          ok: true,
          mfa_required: true,
          mfa_ticket: data.mfa_ticket,
          expires_in: data.expires_in || 300,
        },
        { status: 202 }
      );
    }

    const token = data.access_token || data.token;

    // Handle 200: Successful Login
    if (backendRes.ok && token) {
      const expiresIn = typeof data.expires_in === "number" ? data.expires_in : 43200;

      // Resolve user_id and roles from backend /api/v1/auth/me
      let resolvedUserId = body.user_id ? String(body.user_id) : "";
      let resolvedRoles: string[] = [];

      try {
        const meRes = await backendFetch("/api/v1/auth/me", { method: "GET" }, token);
        if (meRes.ok) {
          const meData = await meRes.json();
          resolvedUserId = String(meData.user_id || resolvedUserId);
          resolvedRoles = Array.isArray(meData.roles) ? meData.roles : [];
        }
      } catch {
        // Fallback to basic fields
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

    // Handle Errors (401, 403, 404, 422, etc.)
    const errorMessage =
      typeof data.detail === "object" && data.detail?.message
        ? data.detail.message
        : typeof data.detail === "string"
        ? data.detail
        : "LOGIN_FAILED";

    return NextResponse.json(
      { ok: false, error: errorMessage },
      { status: backendRes.status || 401 }
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
