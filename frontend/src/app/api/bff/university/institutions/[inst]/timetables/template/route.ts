import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ inst: string }> }
) {
  try {
    const { inst: institutionId } = await params;
    if (!institutionId) {
      return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Dars jadvali shablonini yuklab olish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const format = searchParams.get("format") || "CSV";

    const res = await fetch(
      `${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/timetables/template?format=${encodeURIComponent(format)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      }
    );

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "TIMETABLE_TEMPLATE_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
