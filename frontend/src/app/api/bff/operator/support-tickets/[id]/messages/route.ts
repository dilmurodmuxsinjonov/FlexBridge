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

    const { id: ticketId } = await params;
    if (!ticketId) {
      return NextResponse.json({ ok: false, error: "INVALID_TICKET_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Operator kabinetiga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    if (!body.body || typeof body.body !== "string" || body.body.trim().length === 0) {
      return NextResponse.json(
        { ok: false, error: "INVALID_MESSAGE_BODY", message: "Xabar matni kiritilishi shart." },
        { status: 422 }
      );
    }

    // Pydantic strict payload
    const backendPayload: Record<string, unknown> = {
      body: body.body.trim(),
      internal: Boolean(body.internal),
    };
    if (body.status) backendPayload.status = body.status;
    if (body.file_id) backendPayload.file_id = body.file_id;

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/operator/support-tickets/${encodeURIComponent(ticketId)}/messages`, {
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
        { ok: false, error: data.detail || "POST_MESSAGE_FAILED", message: data.message },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-113",
      ...data,
    }, { status: 201 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
