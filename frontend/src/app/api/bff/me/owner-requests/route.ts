import { proxyAuthed } from "@/lib/server/proxy";

/** GET /api/bff/me/owner-requests */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/me/owner-requests", {
    method: "GET",
    fallbackError: "OWNER_REQUESTS_FETCH_FAILED",
  });
}
