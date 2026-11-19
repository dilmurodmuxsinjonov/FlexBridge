import { proxyAuthed, proxyJsonBody } from "@/lib/server/proxy";

/** GET & POST /api/bff/me/contacts */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/me/contacts", {
    method: "GET",
    fallbackError: "CONTACTS_FETCH_FAILED",
  });
}

export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/me/contacts", "POST", "CONTACT_BIND_FAILED");
}
