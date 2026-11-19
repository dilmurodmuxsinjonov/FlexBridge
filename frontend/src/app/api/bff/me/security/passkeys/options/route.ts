import { proxyJsonBody } from "@/lib/server/proxy";

/** POST /api/bff/me/security/passkeys/options */
export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/me/security/passkeys/options", "POST", "PASSKEY_OPTIONS_FAILED");
}
