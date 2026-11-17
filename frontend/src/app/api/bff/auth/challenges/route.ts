import { NextResponse } from "next/server";
import { verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/auth/challenges
 * Initiates an OTP delivery challenge for phone or email (purpose: REGISTER, LOGIN, RECOVERY).
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

    const payload: Record<string, string> = {
      channel: String(channel).toUpperCase(),
      destination: String(destination).trim(),
      purpose: String(purpose).toUpperCase(),
    };
    if (delivery_method) {
      payload.delivery_method = String(delivery_method).toUpperCase();
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/auth/challenges`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
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
