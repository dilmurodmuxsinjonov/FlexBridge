import { NextResponse } from "next/server";
import { backendFetch, getSession } from "@/lib/server/session";

export async function GET(request: Request) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const limit = searchParams.get("limit") || "50";
  const cursor = searchParams.get("cursor");
  const action = searchParams.get("action");
  const actorId = searchParams.get("actor_id");

  const query = new URLSearchParams({ limit });
  if (cursor) query.set("cursor", cursor);
  if (action) query.set("action", action);
  if (actorId) query.set("actor_id", actorId);

  try {
    const backendRes = await backendFetch(
      `/api/v1/operator/audit-events?${query.toString()}`,
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
      contract_id: data.contract_id || "API-118",
      items: Array.isArray(data.items) ? data.items : [],
      has_more: Boolean(data.has_more),
      next_cursor: data.next_cursor || null,
    });
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
