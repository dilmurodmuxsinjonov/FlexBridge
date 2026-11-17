import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function PUT(request: NextRequest) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Jadval istisnolarini saqlash uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const body = await request.json().catch(() => ({}));
    const { from_date, to_date, exceptions } = body;

    if (!from_date || !to_date || !Array.isArray(exceptions)) {
      return NextResponse.json(
        { ok: false, error: "VALIDATION_FAILED", message: "from_date, to_date va exceptions ro'yxati majburiy." },
        { status: 422 }
      );
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/me/availability/exceptions`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ from_date, to_date, exceptions }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "AVAILABILITY_EXCEPTIONS_SAVE_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-036", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
