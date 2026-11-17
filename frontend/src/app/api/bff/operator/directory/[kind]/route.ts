import { NextResponse } from "next/server";
import { proxyAuthed } from "@/lib/server/proxy";

const ALLOWED_KINDS = new Set(["users", "organizations", "institutions"]);
const ALLOWED_PARAMS = ["q", "role", "status", "limit"] as const;

/** GET masked operator directory listing (users, organizations, institutions). */
export async function GET(
  request: Request,
  context: { params: Promise<{ kind: string }> }
) {
  const { kind } = await context.params;
  if (!ALLOWED_KINDS.has(kind)) {
    return NextResponse.json({ ok: false, error: "NOT_FOUND" }, { status: 404 });
  }
  const incoming = new URL(request.url).searchParams;
  const qs = new URLSearchParams();
  for (const key of ALLOWED_PARAMS) {
    const val = incoming.get(key);
    if (val !== null && val.trim() && val.length <= 120) {
      qs.set(key, val.trim());
    }
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return proxyAuthed(request, `/api/v1/operator/directory/${kind}${suffix}`, {
    method: "GET",
    fallbackError: "DIRECTORY_FETCH_FAILED",
  });
}
