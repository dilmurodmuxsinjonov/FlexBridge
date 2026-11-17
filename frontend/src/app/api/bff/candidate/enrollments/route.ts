import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";
import crypto from "crypto";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Talabalik ma'lumotlarini olish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    const afterId = searchParams.get("after_id");

    const sp = new URLSearchParams();
    sp.set("limit", limit);
    if (afterId) sp.set("after_id", afterId);

    const res = await fetch(`${backendInternalUrl}/api/v1/me/enrollments?${sp.toString()}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "ENROLLMENTS_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-034", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Talabalik arizasini topshirish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const body = await request.json().catch(() => ({}));
    const {
      institution_id,
      program,
      start_date,
      end_date,
      student_ref,
      evidence_note,
      file_ids,
      idempotency_key,
    } = body;

    if (!institution_id || !program || !start_date) {
      return NextResponse.json(
        { ok: false, error: "VALIDATION_FAILED", message: "Muassasa, ta'lim yo'nalishi va boshlanish sanasi majburiy." },
        { status: 422 }
      );
    }

    const finalIdemKey = idempotency_key || `enr-${crypto.randomUUID()}`;

    const payload = {
      institution_id,
      idempotency_key: finalIdemKey,
      program,
      start_date,
      end_date: end_date || null,
      student_ref: student_ref || null,
      file_ids: file_ids || [],
      evidence_note: evidence_note || "",
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/me/enrollments`, {
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
        { ok: false, error: data?.detail || data?.error || "ENROLLMENT_CREATE_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-027", ...data }, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
