import { NextResponse } from "next/server";
import { proxyAuthed } from "@/lib/server/proxy";

/** PATCH toggles an R1-mutable global feature flag with Idempotency-Key and If-Match ETag. */
export async function PATCH(
  request: Request,
  context: { params: Promise<{ code: string }> }
) {
  const { code } = await context.params;
  const trimmed = (code || "").trim();
  if (!trimmed || trimmed.length > 80) {
    return NextResponse.json({ ok: false, error: "INVALID_INPUT" }, { status: 400 });
  }

  const headers: Record<string, string> = {};
  const idempotencyKey = request.headers.get("Idempotency-Key") || request.headers.get("idempotency-key");
  const ifMatch = request.headers.get("If-Match") || request.headers.get("if-match");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
  if (ifMatch) headers["If-Match"] = ifMatch;

  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, `/api/v1/operator/feature-flags/${encodeURIComponent(trimmed)}`, {
    method: "PATCH",
    body,
    headers,
    fallbackError: "FEATURE_FLAG_UPDATE_FAILED",
  });
}
