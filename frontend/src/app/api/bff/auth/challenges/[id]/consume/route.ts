import { NextRequest, NextResponse } from "next/server";
import { verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * POST /api/bff/auth/challenges/[id]/consume
 * Verifies 6-digit OTP code and returns continuation verification token.
 */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const { id } = await context.params;
    if (!id) {
      return NextResponse.json(
        { ok: false, error: "MISSING_CHALLENGE_ID", message: "Challenge ID kiritilishi shart." },
        { status: 400 }
      );
    }

    const body = await request.json();
    const { purpose, code } = body || {};

    if (!purpose || !code) {
      return NextResponse.json(
        { ok: false, error: "MISSING_CODE_OR_PURPOSE", message: "Tasdiqlash kodi va maqsad kiritilishi shart." },
        { status: 400 }
      );
    }

    const payload = {
      purpose: String(purpose).toUpperCase(),
      code: String(code).trim(),
    };

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/auth/challenges/${encodeURIComponent(id)}/consume`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "CODE_VERIFICATION_FAILED");
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
