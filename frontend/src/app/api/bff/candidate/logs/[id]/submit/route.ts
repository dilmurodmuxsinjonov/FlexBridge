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
      return NextResponse.json({ error: "INVALID_LOG_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Kundalikni topshirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/logs/${encodeURIComponent(id)}/submit`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "SUBMIT_DAILY_LOG_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
