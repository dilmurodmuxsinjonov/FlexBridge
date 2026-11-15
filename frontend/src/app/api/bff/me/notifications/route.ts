import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Tizimga kirish talab etiladi" },
      { status: 401 }
    );
  }

  const { searchParams } = new URL(req.url);
  const limit = searchParams.get("limit") || "50";
  const unreadOnly = searchParams.get("unread_only") !== "false";
  const after = searchParams.get("after");

  let query = `limit=${limit}&unread_only=${unreadOnly}`;
  if (after) {
    query += `&after=${after}`;
  }

  try {
    const res = await fetch(`${BACKEND_INTERNAL_URL}/api/v1/me/notifications?${query}`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail?.code || "NOTIFICATIONS_FETCH_FAILED", message: data?.detail?.message || "Bildirishnomalarni yuklab bo'lmadi" },
        { status: res.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-031",
      items: data.items || [],
      next_after: data.next_after || null,
    });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: "PROXY_ERROR", message: err?.message || "Ichki tarmoq xatoligi" },
      { status: 502 }
    );
  }
}
