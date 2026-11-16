import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const ACTIONS = new Set(["claim", "decision"]);

/** POST /api/bff/university/enrollment-requests/[inst]/[case]/(claim|decision) */
export async function POST(request: Request, { params }: { params: Promise<{ inst: string; case: string; action: string }> }) {
  if (!verifyCsrfOrigin(request)) return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  const session = await getSessionFromCookie();
  if (!session?.access_token) return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  const { inst, case: caseId, action } = await params;
  if (!ACTIONS.has(action)) return NextResponse.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  const body = action === "decision" ? JSON.stringify(await request.json().catch(() => ({}))) : undefined;
  try {
    const res = await backendFetch(
      `/api/v1/institutions/${encodeURIComponent(inst)}/enrollment-requests/${encodeURIComponent(caseId)}/${action}`,
      { method: "POST", body, headers: body ? { "Content-Type": "application/json" } : undefined },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json({ ok: false, error: data.detail?.code || "ENROLLMENT_ACTION_FAILED" }, { status: res.status });
    return NextResponse.json({ ok: true, ...data });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR" }, { status: 502 });
  }
}
