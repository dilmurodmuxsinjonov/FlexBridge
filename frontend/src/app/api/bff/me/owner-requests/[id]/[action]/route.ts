import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

const ALLOWED_ACTIONS = new Set(["consent", "cancel"]);

/** POST /api/bff/me/owner-requests/[id]/[action] */
export async function POST(
  request: Request,
  context: { params: Promise<{ id: string; action: string }> }
) {
  const { id, action } = await context.params;
  if (!UUID_RE.test(id) || !ALLOWED_ACTIONS.has(action)) {
    return NextResponse.json({ ok: false, error: "INVALID_OWNER_ACTION" }, { status: 400 });
  }
  return proxyJsonBody(request, `/api/v1/owner-requests/${id}/${action}`, "POST", "OWNER_REQUEST_ACTION_FAILED");
}
