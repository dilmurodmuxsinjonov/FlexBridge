import { proxyAuthed } from "@/lib/server/proxy";

/** GET active/revoked platform staff role grants + authority matrix (API-126). */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/operator/staff-grants", {
    method: "GET",
    fallbackError: "STAFF_GRANTS_FETCH_FAILED",
  });
}

/** POST grants a permanent/long-lived platform role (ADMIN + MFA required). */
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  return proxyAuthed(request, "/api/v1/operator/staff-grants", {
    method: "POST",
    body,
    fallbackError: "STAFF_GRANT_FAILED",
  });
}
