import { NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/auth/challenges
 * Initiates an OTP delivery challenge (REGISTER, LOGIN, RECOVERY, or authenticated CONTACT binding).
 */
export async function POST(request: Request) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const body = await request.json();
    const { channel, destination, purpose, delivery_method } = body || {};

    if (!channel || !destination || !purpose) {
      return NextResponse.json(
        { ok: false, error: "MISSING_REQUIRED_FIELDS", message: "Kanal, manzil va maqsad ko'rsatilishi shart." },
        { status: 400 }
      );
    }

    const normalizedPurpose = String(purpose).toUpperCase();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };

    if (normalizedPurpose === "CONTACT") {
      const session = await getSessionFromCookie();
      if (!session?.access_token) {
        return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
      }
      headers.Authorization = `Bearer ${session.access_token}`;
    }

    const payload: Record<string, string> = {
      channel: String(channel).toUpperCase(),
      destination: String(destination).trim(),
      purpose: normalizedPurpose,
    };
    if (delivery_method) {
      payload.delivery_method = String(delivery_method).toUpperCase();
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/auth/challenges`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "CHALLENGE_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json(
      {
        ok: true,
        ...data,
      },
      { status: backendRes.status }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "INTERNAL_ERROR", message: err instanceof Error ? err.message : "Xatolik yuz berdi" },
      { status: 500 }
    );
  }
}
