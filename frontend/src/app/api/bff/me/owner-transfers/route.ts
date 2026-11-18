import { proxyAuthed } from "@/lib/server/proxy";

/** GET /api/bff/me/owner-transfers */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/me/owner-transfers", {
    method: "GET",
    fallbackError: "OWNER_TRANSFERS_FETCH_FAILED",
  });
}
