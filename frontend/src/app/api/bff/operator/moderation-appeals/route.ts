import { proxyAuthed } from "@/lib/server/proxy";

/** GET moderation rejection appeals queue (MODERATOR + MFA). */
export async function GET(request: Request) {
  const incoming = new URL(request.url).searchParams;
  const qs = new URLSearchParams();
  for (const key of ["limit", "after"] as const) {
    const val = incoming.get(key);
    if (val !== null && val.trim() && val.length <= 64) {
      qs.set(key, val.trim());
    }
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return proxyAuthed(request, `/api/v1/operator/moderation-appeals${suffix}`, {
    method: "GET",
    fallbackError: "MODERATION_APPEALS_FETCH_FAILED",
  });
}
