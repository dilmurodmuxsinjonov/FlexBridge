import { NextResponse } from "next/server";
import { setSessionCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/auth/register
 * Completes candidate user registration and immediately establishes authenticated session.
 */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const body = await request.json();
    const {
      verification_token,
      display_name,
      password,
      adult_confirmed,
      terms_version,
      privacy_version,
      roles,
      enable_totp,
    } = body || {};

    if (!verification_token || !display_name || !password) {
      return NextResponse.json(
        { ok: false, error: "MISSING_REQUIRED_FIELDS", message: "Ism, parol va tasdiqlash tokeni kiritilishi shart." },
        { status: 400 }
      );
    }

    if (password.length < 12) {
      return NextResponse.json(
        { ok: false, error: "PASSWORD_TOO_SHORT", message: "Parol kamida 12 ta belgidan iborat bo'lishi shart." },
        { status: 400 }
      );
    }

    if (!adult_confirmed) {
      return NextResponse.json(
        { ok: false, error: "ADULT_CONFIRMATION_REQUIRED", message: "Voyaga yetganlik (18 yosh) tasdiqlanishi shart." },
        { status: 400 }
      );
    }

    const payload = {
      verification_token,
      display_name: String(display_name).trim(),
      password,
      adult_confirmed: Boolean(adult_confirmed),
      terms_version: terms_version || "2026.1",
      privacy_version: privacy_version || "2026.1",
      roles: Array.isArray(roles) && roles.length > 0 ? roles : ["CANDIDATE"],
      enable_totp: Boolean(enable_totp),
    };

    const registerRes = await fetch(`${backendInternalUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    const regData = await registerRes.json().catch(() => ({}));

    if (!registerRes.ok) {
      const errMsg = typeof regData.detail === "object" ? (regData.detail?.message || regData.detail?.code) : (regData.detail || "REGISTRATION_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: regData.detail },
        { status: registerRes.status }
      );
    }

    // Registration succeeded: immediately establish session via begin_login
    let loggedIn = false;
    try {
      const loginRes = await fetch(`${backendInternalUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          user_id: regData.id,
          password: password,
        }),
      });

      if (loginRes.ok) {
        const loginData = await loginRes.json();
        const token = loginData.access_token || loginData.token;
        if (token) {
          const expiresIn = typeof loginData.expires_in === "number" ? loginData.expires_in : 43200;
          await setSessionCookie({
            token,
            user_id: regData.id,
            roles: Array.isArray(regData.roles) ? regData.roles : ["CANDIDATE"],
            expires_at: Math.floor(Date.now() / 1000) + expiresIn,
          });
          loggedIn = true;
        }
      }
    } catch {
      // Login attempt failed, user can still log in manually via /kirish
    }

    return NextResponse.json(
      {
        ok: true,
        user: regData,
        logged_in: loggedIn,
      },
      { status: 201 }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "INTERNAL_ERROR", message: err instanceof Error ? err.message : "Xatolik yuz berdi" },
      { status: 500 }
    );
  }
}
