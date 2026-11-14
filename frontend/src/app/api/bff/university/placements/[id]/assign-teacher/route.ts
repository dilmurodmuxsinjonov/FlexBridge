import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { id: placementId } = await params;
    if (!placementId) {
      return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "O'qituvchi biriktirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const { institution_id, supervisor_id, supervision_id } = body;

    if (!institution_id || !supervisor_id || !supervision_id) {
      return NextResponse.json(
        { ok: false, error: "MISSING_REQUIRED_FIELDS", message: "institution_id, supervisor_id va supervision_id talab qilinadi." },
        { status: 422 }
      );
    }

    const idempotencyKey =
      (typeof body.idempotency_key === "string" && body.idempotency_key.length >= 8)
        ? body.idempotency_key
        : (request.headers.get("Idempotency-Key") || `flx-nominate-${crypto.randomUUID()}`);

    const backendPayload = {
      institution_id,
      supervisor_id,
      supervision_id,
      idempotency_key: idempotencyKey,
    };

    const backendRes = await fetch(
      `${backendInternalUrl}/api/v1/placements/${encodeURIComponent(placementId)}/academic-assignments`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(backendPayload),
        cache: "no-store",
      }
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "ASSIGN_TEACHER_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-102",
      assignment: data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
