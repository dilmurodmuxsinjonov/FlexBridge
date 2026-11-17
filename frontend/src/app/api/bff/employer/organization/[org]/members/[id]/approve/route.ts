import { NextResponse } from "next/server";
import { proxyAuthed, UUID_RE } from "@/lib/server/proxy";

/** POST — owner approves a pending join request (role from the request). */
export async function POST(request: Request, context: { params: Promise<{ org: string; id: string }> }) {
  const { org, id } = await context.params;
  if (!UUID_RE.test(org) || !UUID_RE.test(id)) return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  return proxyAuthed(request, `/api/v1/organizations/${org}/members/${id}/approve`, { method: "POST", body: {}, fallbackError: "MEMBER_APPROVE_FAILED" });
}
