import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

function verifyOrigin(req: NextRequest): boolean {
  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (!origin || !host) return true;
  try {
    const originHost = new URL(origin).host;
    return originHost === host;
  } catch {
    return false;
  }
}

export async function GET(req: NextRequest) {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Tizimga kirish talab etiladi" },
      { status: 401 }
    );
  }

  const { searchParams } = new URL(req.url);
  const page = searchParams.get("page") || "1";
  const pageSize = searchParams.get("page_size") || "20";

  try {
    const res = await fetch(
      `${BACKEND_INTERNAL_URL}/api/v1/me/saved-opportunities?page=${page}&page_size=${pageSize}`,
      {
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
        { ok: false, error: data?.detail?.code || "SAVED_OPPORTUNITIES_FETCH_FAILED", message: data?.detail?.message || "Saqlangan e'lonlarni yuklab bo'lmadi" },
        { status: res.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-037",
      items: data.items || [],
      total: data.total ?? (data.items ? data.items.length : 0),
      page: data.page ?? Number(page),
      page_size: data.page_size ?? Number(pageSize),
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "PROXY_ERROR", message: (err instanceof Error && err.message) || "Ichki tarmoq xatoligi" },
      { status: 502 }
    );
  }
}

export async function POST(req: NextRequest) {
  if (!verifyOrigin(req)) {
    return NextResponse.json(
      { ok: false, error: "CSRF_ORIGIN_MISMATCH", message: "Xavfsizlik tekshiruvidan o'tmadi" },
      { status: 403 }
    );
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Tizimga kirish talab etiladi" },
      { status: 401 }
    );
  }

  const body = await req.json().catch(() => ({}));
  if (!body.opportunity_id) {
    return NextResponse.json(
      { ok: false, error: "VALIDATION_ERROR", message: "opportunity_id ko'rsatilishi shart" },
      { status: 422 }
    );
  }

  try {
    const res = await fetch(`${BACKEND_INTERNAL_URL}/api/v1/saved-opportunities`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        opportunity_id: body.opportunity_id,
        candidate_id: body.candidate_id || undefined,
        toggle: Boolean(body.toggle),
      }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail?.code || "SAVE_FAILED", message: data?.detail?.message || "E'lonni saqlab bo'lmadi" },
        { status: res.status }
      );
    }

    return NextResponse.json(
      {
        ok: true,
        contract_id: "API-004",
        saved: data.saved,
        opportunity_id: data.opportunity_id,
        id: data.id,
      },
      { status: res.status === 201 ? 201 : 200 }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "PROXY_ERROR", message: (err instanceof Error && err.message) || "Ichki tarmoq xatoligi" },
      { status: 502 }
    );
  }
}
