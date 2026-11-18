import { proxyJsonBody } from "@/lib/server/proxy";

/** POST /api/bff/university/supervisions (`POST /api/v1/student-supervisions`) */
export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/student-supervisions", "POST", "SUPERVISION_CREATE_FAILED");
}
