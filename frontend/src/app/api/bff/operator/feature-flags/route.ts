import { proxyAuthed } from "@/lib/server/proxy";

/** GET global feature flags catalog with version numbers for optimistic If-Match updates. */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/operator/feature-flags", {
    method: "GET",
    fallbackError: "FEATURE_FLAGS_FETCH_FAILED",
  });
}
