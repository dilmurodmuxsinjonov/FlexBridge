import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_PLACEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Amaliyot shartlarini qabul qilish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    if (!body.terms_id || typeof body.terms_id !== "string") {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "terms_id talab qilinadi." },
        { status: 422 }
      );
    }
    const version = Number(body.version);
    if (!version || version < 1) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "version kamida 1 bo'lishi kerak." },
        { status: 422 }
      );
    }
    const idempotencyKey = String(body.idempotency_key || `cand-accept-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`);

    // Backend TermsRequest has extra='forbid'
    const backendPayload = {
      terms_id: body.terms_id,
      version,
      idempotency_key: idempotencyKey,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/placements/${encodeURIComponent(id)}/accept`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(backendPayload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "PLACEMENT_ACCEPT_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
