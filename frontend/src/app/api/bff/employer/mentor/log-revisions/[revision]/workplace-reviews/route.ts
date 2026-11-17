import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const ALLOWED_DECISIONS = ["APPROVED", "CHANGES_REQUESTED", "REJECTED"] as const;

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ revision: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { revision } = await params;
    if (!revision) {
      return NextResponse.json(
        { ok: false, error: "REVISION_ID_REQUIRED", message: "Tahrir identifikatori ko'rsatilmagan." },
        { status: 400 }
      );
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Mentor xulosasini topshirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const { decision, comment } = body;

    if (!decision || !ALLOWED_DECISIONS.includes(decision)) {
      return NextResponse.json(
        {
          ok: false,
          error: "INVALID_DECISION",
          message: `Noto'g'ri qaror qiymati. Ruxsat berilgan: ${ALLOWED_DECISIONS.join(", ")}`,
        },
        { status: 422 }
      );
    }

    const idempotencyKey =
      (typeof body.idempotency_key === "string" && body.idempotency_key.length >= 8)
        ? body.idempotency_key
        : (request.headers.get("Idempotency-Key") || `flx-mentor-rev-${crypto.randomUUID()}`);

    const backendPayload: { decision: string; comment?: string } = {
      decision,
    };
    if (typeof comment === "string" && comment.trim().length > 0) {
      backendPayload.comment = comment.trim();
    }

    const backendRes = await backendFetch(
      `/api/v1/log-revisions/${encodeURIComponent(revision)}/workplace-reviews`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(backendPayload),
      },
      session.access_token
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorMessage =
        typeof data.detail === "object" && data.detail?.code
          ? data.detail.code
          : typeof data.detail === "string"
          ? data.detail
          : "SUBMIT_MENTOR_REVIEW_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data.message || errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-092",
      review: data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
