import { proxyAuthed } from "@/lib/server/proxy";

/** GET /api/bff/me/contacts */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/me/contacts", {
    method: "GET",
    fallbackError: "CONTACTS_FETCH_FAILED",
  });
}
