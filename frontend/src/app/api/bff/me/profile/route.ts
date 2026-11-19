import { proxyJsonBody } from "@/lib/server/proxy";

export async function PATCH(request: Request) {
  return proxyJsonBody(request, "/api/v1/me/profile", "PATCH", "PROFILE_UPDATE_FAILED");
}
