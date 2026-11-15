import { NextRequest, NextResponse } from "next/server";
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

    const { id: interviewId } = await params;
    if (!interviewId) {
      return NextResponse.json({ ok: false, error: "INVALID_INTERVIEW_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Suhbatga javob berish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const allowedResponses = ["ACCEPTED", "DECLINED", "RESCHEDULE_REQUESTED", "COMPLETED", "NO_SHOW"];
    const respUpper = (body.response || "").toString().trim().toUpperCase();

    if (!allowedResponses.includes(respUpper)) {
      return NextResponse.json(
        { ok: false, error: "INVALID_RESPONSE", message: `Javob turi faqat quyidagilardan biri bo'lishi mumkin: ${allowedResponses.join(", ")}` },
        { status: 422 }
      );
    }

    // backend InterviewResponseRequest model expects { response: string, note?: string | null } with extra='forbid'
    const payload: { response: string; note?: string | null } = {
      response: respUpper,
    };
    if (body.note !== undefined && body.note !== null) {
      payload.note = String(body.note);
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/interviews/${encodeURIComponent(interviewId)}/responses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "INTERVIEW_RESPONSE_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-042",
      ...data,
    }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
