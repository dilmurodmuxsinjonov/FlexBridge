import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";
import crypto from "crypto";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Talabalikni yakunlash uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const { id } = await params;
    if (!id) {
      return NextResponse.json({ ok: false, error: "INVALID_IDENTIFIER" }, { status: 400 });
    }

    const body = await request.json().catch(() => ({}));
    const { reason, effective_end_date, idempotency_key } = body;

    if (!reason || typeof reason !== "string" || reason.trim().length < 15) {
      return NextResponse.json(
        { ok: false, error: "VALIDATION_FAILED", message: "Yakunlash sababi kamida 15 ta belgidan iborat bo'lishi shart." },
        { status: 422 }
      );
    }

    const finalIdemKey = idempotency_key || `end-${crypto.randomUUID()}`;

    const payload = {
      idempotency_key: finalIdemKey,
      reason: reason.trim(),
      effective_end_date: effective_end_date || null,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/me/enrollments/${id}/end`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "ENROLLMENT_END_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
