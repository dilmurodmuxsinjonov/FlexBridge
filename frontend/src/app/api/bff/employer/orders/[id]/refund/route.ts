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

    const { id: orderId } = await params;
    if (!orderId) {
      return NextResponse.json({ ok: false, error: "INVALID_ORDER_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Ish beruvchi kabinetiga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const amountUzs = Number(body.amount_uzs);
    const reason = typeof body.reason === "string" ? body.reason.trim() : "";

    if (!amountUzs || isNaN(amountUzs) || amountUzs <= 0) {
      return NextResponse.json(
        { ok: false, error: "INVALID_REFUND_AMOUNT", message: "Qaytarish summasi 0 dan katta bo'lishi shart." },
        { status: 422 }
      );
    }

    if (reason.length < 15) {
      return NextResponse.json(
        { ok: false, error: "INVALID_REFUND_REASON", message: "Qaytarish sababi kamida 15 ta belgidan iborat bo'lishi shart." },
        { status: 422 }
      );
    }

    const backendPayload = {
      amount_uzs: Math.round(amountUzs),
      reason,
    };

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/orders/${encodeURIComponent(orderId)}/refund-requests`, {
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
        { ok: false, error: data.detail || "REQUEST_REFUND_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-095",
      ...data,
    }, { status: 201 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
