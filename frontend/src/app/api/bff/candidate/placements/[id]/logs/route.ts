import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_PLACEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Amaliyot kundaliklarini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const forwardParams = new URLSearchParams();

    const fromDate = searchParams.get("from_date");
    if (fromDate) forwardParams.set("from_date", fromDate);

    const toDate = searchParams.get("to_date");
    if (toDate) forwardParams.set("to_date", toDate);

    const status = searchParams.get("status");
    if (status) forwardParams.set("status", status);

    const page = searchParams.get("page");
    if (page) forwardParams.set("page", page);

    const pageSize = searchParams.get("page_size");
    if (pageSize) forwardParams.set("page_size", pageSize);

    forwardParams.set("include_tasks", "true");
    forwardParams.set("include_reviews", "true");

    const queryString = forwardParams.toString();
    const endpoint = `${backendInternalUrl}/api/v1/placements/${encodeURIComponent(id)}/logs${queryString ? `?${queryString}` : ""}`;

    const res = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "PLACEMENT_LOGS_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
