import { NextResponse } from "next/server";
import { backendFetch, completeAuthenticatedSession, verifyCsrfOrigin } from "@/lib/server/session";
import { backendErrorCode, readJsonObject } from "@/lib/server/proxy";

/** POST /api/auth/passkeys/verify */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const body = await readJsonObject(request);
  const ceremonyToken = typeof body?.ceremony_token === "string" ? body.ceremony_token.trim() : "";
  const credential = body?.credential;
  const portal = typeof body?.portal === "string" ? body.portal : undefined;

  if (!ceremonyToken || !credential || typeof credential !== "object") {
    return NextResponse.json({ ok: false, error: "PASSKEY_CREDENTIAL_REQUIRED" }, { status: 400 });
  }

  try {
    const backendRes = await backendFetch("/api/v1/auth/passkeys/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ ceremony_token: ceremonyToken, credential }),
    });
    const data = await backendRes.json().catch(() => ({}));
    const token = data.access_token || data.token;

    if (backendRes.ok && token) {
      const expiresIn = typeof data.expires_in === "number" ? data.expires_in : 43200;
      const result = await completeAuthenticatedSession({
        token,
        expiresIn,
        portal,
      });

      if (!result.ok) {
        return NextResponse.json(
          { ok: false, error: result.error, message: result.message },
          { status: result.status }
        );
      }

      return NextResponse.json({
        ok: true,
        user_id: result.user_id,
        roles: result.roles,
      });
    }

    return NextResponse.json(
      { ok: false, error: backendErrorCode(backendRes.status, data, "PASSKEY_VERIFICATION_FAILED") },
      { status: backendRes.status || 401 }
    );
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
