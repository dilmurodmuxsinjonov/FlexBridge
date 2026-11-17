import { proxyAuthed } from "@/lib/server/proxy";

/** POST runs a non-destructive retention dry-run evaluation (COMPLIANCE + MFA + Idempotency-Key). */
export async function POST(request: Request) {
  const headers: Record<string, string> = {};
  const idempotencyKey = request.headers.get("Idempotency-Key") || request.headers.get("idempotency-key");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, "/api/v1/operations/retention-executions", {
    method: "POST",
    body,
    headers,
    fallbackError: "RETENTION_EVALUATION_FAILED",
  });
}
