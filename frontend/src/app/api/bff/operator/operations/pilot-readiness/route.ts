import { proxyAuthed } from "@/lib/server/proxy";

/** GET R1 pilot readiness and DR/circuit status (ADMIN or COMPLIANCE). */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/operations/pilot-readiness", {
    method: "GET",
    fallbackError: "PILOT_READINESS_FETCH_FAILED",
  });
}
