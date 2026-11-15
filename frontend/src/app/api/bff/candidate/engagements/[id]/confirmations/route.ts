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
        { error: "AUTH_REQUIRED", message: "Ish holatini tasdiqlash uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const action = String(body.action || "CONFIRM_START").toUpperCase();
    const allowedActions = ["CONFIRM_START", "CONFIRM_END", "DISPUTE_START", "DISPUTE_END"];
    if (!allowedActions.includes(action)) {
      return NextResponse.json(
        { error: "INVALID_ACTION", message: `Yaroqsiz amal. Ruxsat etilgan: ${allowedActions.join(", ")}` },
        { status: 422 }
      );
    }

    // Backend EngagementConfirmRequest has extra='forbid'
    const backendPayload: Record<string, unknown> = {
      action,
      party: "CANDIDATE",
    };
    if (body.note && typeof body.note === "string") {
      backendPayload.note = body.note.trim();
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/engagements/${encodeURIComponent(id)}/confirmations`, {
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
        data || { error: "ENGAGEMENT_CONFIRMATION_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
