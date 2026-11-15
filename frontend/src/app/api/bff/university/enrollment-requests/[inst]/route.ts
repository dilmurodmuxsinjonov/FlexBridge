import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

/** GET /api/bff/university/enrollment-requests/[inst]?mine= — open student-status requests for this institution. */
export async function GET(request: NextRequest, { params }: { params: Promise<{ inst: string }> }) {
  const session = await getSessionFromCookie();
  if (!session?.access_token) return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  const { inst } = await params;
  const mine = request.nextUrl.searchParams.get("mine") === "true" ? "?mine=true" : "";
  try {
    const res = await backendFetch(`/api/v1/institutions/${encodeURIComponent(inst)}/enrollment-requests${mine}`, { method: "GET" }, session.access_token);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json({ ok: false, error: data.detail?.code || "ENROLLMENT_QUEUE_FAILED" }, { status: res.status });
    return NextResponse.json({ ok: true, items: Array.isArray(data.items) ? data.items : [] });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR" }, { status: 502 });
  }
}
