import { NextResponse } from "next/server";
import { proxyJsonBody, UUID_RE } from "@/lib/server/proxy";

/** POST /api/bff/employer/moderation/actions/[id]/appeals (`API-111` appellant submit) */
export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ ok: false, error: "INVALID_MODERATION_ACTION_ID" }, { status: 400 });
  }
  return proxyJsonBody(
    request,
    `/api/v1/moderation/actions/${encodeURIComponent(id)}/appeals`,
    "POST",
    "MODERATION_APPEAL_SUBMIT_FAILED"
  );
}
