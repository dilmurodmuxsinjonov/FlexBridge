import { proxyAuthed } from "@/lib/server/proxy";

/** GET account recovery review queue (ADMIN / SUPPORT + MFA). */
export async function GET(request: Request) {
  const incoming = new URL(request.url).searchParams;
  const qs = new URLSearchParams();
  for (const key of ["status", "limit"] as const) {
    const val = incoming.get(key);
    if (val !== null && val.trim() && val.length <= 64) {
      qs.set(key, val.trim());
    }
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return proxyAuthed(request, `/api/v1/operator/recovery-requests${suffix}`, {
    method: "GET",
    fallbackError: "RECOVERY_REQUESTS_FETCH_FAILED",
  });
}
