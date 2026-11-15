import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Operator kabinetiga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status");
    const category = searchParams.get("category");
    const priority = searchParams.get("priority");
    const assigneeId = searchParams.get("assignee_id");
    const limit = searchParams.get("limit") || "20";
    const cursor = searchParams.get("cursor");

    const query = new URLSearchParams({ limit });
    if (status) query.set("status", status);
    if (category) query.set("category", category);
    if (priority) query.set("priority", priority);
    if (assigneeId) query.set("assignee_id", assigneeId);
    if (cursor) query.set("cursor", cursor);

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/operator/support-tickets?${query.toString()}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "FETCH_TICKETS_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-112",
      items: Array.isArray(data.items) ? data.items : (Array.isArray(data) ? data : []),
      next_cursor: data.next_cursor || null,
      total: data.total,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
