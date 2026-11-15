import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Mentorlik navbatini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    const cursor = searchParams.get("cursor");

    const qs = new URLSearchParams({ limit });
    if (cursor) qs.set("cursor", cursor);

    const backendRes = await backendFetch(
      `/api/v1/me/mentor-review-queue?${qs.toString()}`,
      { method: "GET" },
      session.access_token
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorMessage =
        typeof data.detail === "object" && data.detail?.code
          ? data.detail.code
          : typeof data.detail === "string"
          ? data.detail
          : "FETCH_MENTOR_QUEUE_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data.message || errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-090",
      items: data.items || [],
      total: data.total ?? (data.items || []).length,
      next_cursor: data.next_cursor || null,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
