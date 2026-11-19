import { proxyJsonBody } from "@/lib/server/proxy";

export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/me/security/password", "POST", "PASSWORD_CHANGE_FAILED");
}
