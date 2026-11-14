import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_CASE_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Tekshiruv xulosasini yuborish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const decision = body.decision;
    const expectedRevision = Number(body.expected_revision) || 1;
    const reason = typeof body.reason === "string" ? body.reason.trim() : "";

    if (!["APPROVE", "REJECT", "NEEDS_INFO"].includes(decision)) {
      return NextResponse.json(
        { error: "INVALID_DECISION", message: "decision APPROVE, REJECT yoki NEEDS_INFO bo'lishi shart" },
        { status: 422 }
      );
    }

    if (!reason || reason.length < 15) {
      return NextResponse.json(
        { error: "INVALID_REASON", message: "Asoslantirish kamida 15 ta belgidan iborat bo'lishi shart" },
        { status: 422 }
      );
    }

    const payload = {
      decision,
      expected_revision: expectedRevision,
      reason,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/operator/verification-cases/${encodeURIComponent(id)}/decide`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMessage =
        typeof data?.detail === "object" && data?.detail?.message
          ? data.detail.message
          : typeof data?.detail === "string"
          ? data.detail
          : data?.error || "DECISION_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, detail: data?.detail },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-110", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
