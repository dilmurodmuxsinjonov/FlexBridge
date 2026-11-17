import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_USER_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Sessiyalarni bekor qilish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const reason = typeof body.reason === "string" ? body.reason.trim() : "";
    const incidentId = body.incident_id || null;

    if (!reason || reason.length < 5) {
      return NextResponse.json(
        { error: "INVALID_REASON", message: "Bekor qilish asosi (reason) kamida 5 ta belgidan iborat bo'lishi shart" },
        { status: 422 }
      );
    }

    const payload = {
      reason,
      incident_id: incidentId,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/operator/users/${encodeURIComponent(id)}/revoke-sessions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMessage =
        typeof data?.detail === "object" && data?.detail?.code
          ? data.detail.code
          : typeof data?.detail === "object" && data?.detail?.message
          ? data.detail.message
          : typeof data?.detail === "string"
          ? data.detail
          : data?.error || "REVOKE_SESSIONS_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data?.detail?.message || errorMessage },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-120", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
