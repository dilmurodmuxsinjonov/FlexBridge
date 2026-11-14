import { NextResponse } from "next/server";
import { backendFetch, getSession } from "@/lib/server/session";

export async function GET(request: Request) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") || "50";
  const after = searchParams.get("after");

  const query = new URLSearchParams({ limit });
  if (after) query.set("after", after);

  try {
    const backendRes = await backendFetch(
      `/api/v1/me/academic-review-queue?${query.toString()}`,
      { method: "GET" },
      session.token
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorMessage =
        typeof data.detail === "object" && data.detail?.message
          ? data.detail.message
          : typeof data.detail === "string"
          ? data.detail
          : "REQUEST_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      items: Array.isArray(data.items) ? data.items : [],
      next_after: data.next_after || null,
    });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
