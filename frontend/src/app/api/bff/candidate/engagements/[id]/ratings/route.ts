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
      return NextResponse.json({ error: "INVALID_ENGAGEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Baholash yuborish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    if (!body || !Array.isArray(body.scores) || body.scores.length === 0) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "Kamida bitta mezon bo'yicha ball kiritilishi shart." },
        { status: 422 }
      );
    }

    // Format & sanitize scores for backend extra="forbid"
    const formattedScores = body.scores.map((s: { criterion_id?: string; score?: number }) => ({
      criterion_id: String(s.criterion_id || ""),
      score: Number(s.score || 0),
    }));

    const backendPayload: Record<string, unknown> = {
      scores: formattedScores,
    };

    if (body.rubric_id && typeof body.rubric_id === "string") {
      backendPayload.rubric_id = body.rubric_id.trim();
    }
    if (body.comment && typeof body.comment === "string") {
      backendPayload.comment = body.comment.trim();
    }
    if (body.idempotency_key && typeof body.idempotency_key === "string") {
      backendPayload.idempotency_key = body.idempotency_key.trim();
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/engagements/${encodeURIComponent(id)}/ratings`, {
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
        data || { error: "SUBMIT_RATING_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
