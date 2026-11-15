import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ inst: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { inst: institutionId } = await params;
    if (!institutionId) {
      return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Hisobot eksport qilish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));

    const rawFormat = typeof body.format === "string" ? body.format.trim().toUpperCase() : "PDF";
    if (rawFormat !== "PDF" && rawFormat !== "JSON") {
      return NextResponse.json(
        { ok: false, error: "INVALID_EXPORT_FORMAT", message: "Format faqat 'PDF' yoki 'JSON' bo'lishi mumkin." },
        { status: 422 }
      );
    }

    const idempotencyKey = typeof body.idempotency_key === "string" && body.idempotency_key.trim().length >= 8
      ? body.idempotency_key.trim()
      : crypto.randomUUID();

    const includeDetails = body.include_details !== false;

    // Strict Pydantic extra="forbid" payload
    const backendPayload = {
      idempotency_key: idempotencyKey,
      format: rawFormat,
      include_details: includeDetails,
    };

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/exports`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(backendPayload),
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "EXPORT_FAILED", message: data.message || "Hisobotni yaratishda xatolik yuz berdi" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      ...data,
    }, { status: 201 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
