import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

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
        { ok: false, error: "AUTH_REQUIRED", message: "OTM dars jadvalini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const groupCode = searchParams.get("group_code");
    const query = new URLSearchParams();
    if (groupCode) query.set("group_code", groupCode);
    const qs = query.toString() ? `?${query.toString()}` : "";

    const res = await fetch(
      `${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/timetables${qs}`,
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
        { ok: false, error: data?.detail || data?.error || "TIMETABLE_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ inst: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const { inst: institutionId } = await params;
    if (!institutionId) {
      return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "OTM dars jadvalini saqlash uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const res = await fetch(
      `${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/timetables`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      }
    );

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "TIMETABLE_SAVE_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
