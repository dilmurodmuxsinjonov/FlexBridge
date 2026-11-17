import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

/**
 * GET /api/bff/me/workspaces
 * Organizations and institutions where the signed-in user currently holds a grant,
 * so portals can pick the workspace instead of asking staff to paste UUIDs.
 */
export async function GET() {
  const session = await getSessionFromCookie();
  if (!session?.access_token) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }
  try {
    const res = await backendFetch("/api/v1/me/workspaces", { method: "GET" }, session.access_token);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json({ ok: false, error: "WORKSPACES_FAILED", detail: data.detail }, { status: res.status });
    }
    return NextResponse.json({
      ok: true,
      organizations: Array.isArray(data.organizations) ? data.organizations : [],
      institutions: Array.isArray(data.institutions) ? data.institutions : [],
    });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR", message: "Ichki tarmoq xatoligi" }, { status: 502 });
  }
}
