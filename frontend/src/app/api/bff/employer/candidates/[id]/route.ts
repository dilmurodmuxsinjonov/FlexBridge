import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

/** GET /api/bff/employer/candidates/[id] — candidate detail with resume sections (API-087-DETAIL). */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSessionFromCookie();
  if (!session?.access_token) return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  const { id } = await params;
  try {
    const res = await backendFetch(`/api/v1/employer/candidates/${encodeURIComponent(id)}`, { method: "GET" }, session.access_token);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json({ ok: false, error: data.detail?.code || "CANDIDATE_DETAIL_FAILED" }, { status: res.status });
    return NextResponse.json({ ok: true, ...data });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR" }, { status: 502 });
  }
}
