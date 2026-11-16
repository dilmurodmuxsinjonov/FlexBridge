import { NextRequest } from "next/server";
import { forwardRecovery } from "../_proxy";

/** GET /api/bff/auth/recovery/[id] — status of a recovery request (X-Recovery-Token header). */
export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  return forwardRecovery(`/auth/recovery/${encodeURIComponent(id)}`, {
    method: "GET",
    recoveryToken: request.headers.get("x-recovery-token"),
  });
}
