import { proxyJsonBody } from "@/lib/server/proxy";

/** POST /api/bff/me/security/passkeys/verify */
export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/me/security/passkeys/verify", "POST", "PASSKEY_REGISTER_FAILED");
}
