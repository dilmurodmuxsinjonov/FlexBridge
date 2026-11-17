import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Jadval ma'lumotlarini olish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const { searchParams } = new URL(request.url);
    const fromDate = searchParams.get("from_date");
    const days = searchParams.get("days") || "28";

    const sp = new URLSearchParams();
    if (fromDate) sp.set("from_date", fromDate);
    sp.set("days", days);

    const res = await fetch(`${backendInternalUrl}/api/v1/me/availability?${sp.toString()}`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "AVAILABILITY_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-035", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Jadvalni saqlash uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const body = await request.json().catch(() => ({}));
    const rawRules = Array.isArray(body.rules) ? body.rules : [];

    // Validate rules
    for (const r of rawRules) {
      const wd = Number(r.weekday);
      const sm = Number(r.start_minute);
      const em = Number(r.end_minute);
      if (isNaN(wd) || wd < 1 || wd > 7) {
        return NextResponse.json(
          { ok: false, error: "INVALID_WEEKDAY", message: "weekday 1 dan 7 gacha bo'lishi shart" },
          { status: 422 }
        );
      }
      if (isNaN(sm) || sm < 0 || sm >= 1440 || isNaN(em) || em <= 0 || em > 1440 || sm >= em) {
        return NextResponse.json(
          { ok: false, error: "INVALID_MINUTES", message: "start_minute end_minute dan kichik bo'lishi shart" },
          { status: 422 }
        );
      }
    }

    const todayStr = new Date().toISOString().split("T")[0];
    const rules = rawRules.map((r: { weekday: number; start_minute: number; end_minute: number; valid_from?: string; valid_to?: string | null }) => ({
      weekday: Number(r.weekday),
      start_minute: Number(r.start_minute),
      end_minute: Number(r.end_minute),
      valid_from: r.valid_from || todayStr,
      valid_to: r.valid_to || null,
      timezone: "Asia/Tashkent",
    }));

    const res = await fetch(`${backendInternalUrl}/api/v1/me/availability`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ rules }),
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = typeof data?.detail === "string" ? data.detail : data?.error || "AVAILABILITY_UPDATE_FAILED";
      return NextResponse.json({ ok: false, error: msg }, { status: res.status });
    }

    return NextResponse.json({ ok: true, contract_id: "API-028", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
