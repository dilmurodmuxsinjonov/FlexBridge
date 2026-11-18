import { proxyPublic } from "@/lib/server/proxy";

/** GET /api/bff/public/services (`API-011`) */
export async function GET() {
  return proxyPublic("/api/v1/services/public", "SERVICES_UNAVAILABLE", "public, max-age=300, stale-while-revalidate=600");
}
