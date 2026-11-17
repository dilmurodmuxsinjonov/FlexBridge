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
      return NextResponse.json({ error: "INVALID_RATING_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "E'tiroz bildirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const reason = typeof body.reason === "string" ? body.reason.trim() : "";
    if (reason.length < 10) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "E'tiroz sababi kamida 10 ta belgidan iborat bo'lishi shart." },
        { status: 422 }
      );
    }

    const backendPayload: Record<string, unknown> = {
      reason,
      category: typeof body.category === "string" && body.category.trim() ? body.category.trim() : "FACTUAL_DISPUTE",
    };
    if (body.evidence_notes && typeof body.evidence_notes === "string") {
      backendPayload.evidence_notes = body.evidence_notes.trim();
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/ratings/${encodeURIComponent(id)}/appeals`, {
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
        data || { error: "SUBMIT_APPEAL_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
