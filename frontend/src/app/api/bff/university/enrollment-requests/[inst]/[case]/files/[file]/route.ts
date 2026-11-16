import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

/** GET .../[inst]/[case]/files/[file] — short-lived signed URL for one evidence file (audited). */
export async function GET(_request: Request, { params }: { params: Promise<{ inst: string; case: string; file: string }> }) {
  const session = await getSessionFromCookie();
  if (!session?.access_token) return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  const { inst, case: caseId, file } = await params;
  try {
    const res = await backendFetch(
      `/api/v1/institutions/${encodeURIComponent(inst)}/enrollment-requests/${encodeURIComponent(caseId)}/files/${encodeURIComponent(file)}/download`,
      { method: "GET" },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return NextResponse.json({ ok: false, error: data.detail?.code || "EVIDENCE_DOWNLOAD_FAILED" }, { status: res.status });
    return NextResponse.json({ ok: true, signed_url: data.signed_url, expires_in_seconds: data.expires_in_seconds });
  } catch {
    return NextResponse.json({ ok: false, error: "PROXY_ERROR" }, { status: 502 });
  }
}
