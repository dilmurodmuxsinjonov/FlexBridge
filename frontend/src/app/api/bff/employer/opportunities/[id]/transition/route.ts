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

    const { id: opportunityId } = await params;
    if (!opportunityId) {
      return NextResponse.json({ ok: false, error: "INVALID_OPPORTUNITY_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Vakansiya holatini o'zgartirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    if (!body.status || !["PAUSED", "CLOSED"].includes(body.status.toUpperCase())) {
      return NextResponse.json(
        { ok: false, error: "INVALID_STATUS", message: "Yangi holat faqat PAUSED yoki CLOSED bo'lishi mumkin." },
        { status: 422 }
      );
    }

    // backend expects { "status": "PAUSED" } or { "status": "CLOSED" } with extra='forbid'
    const payload = {
      status: body.status.toUpperCase(),
    };

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/opportunities/${encodeURIComponent(opportunityId)}/transition`, {
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
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "TRANSITION_OPPORTUNITY_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-082",
      ...data,
    }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
