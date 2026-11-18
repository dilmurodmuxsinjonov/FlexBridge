import { proxyPublic } from "@/lib/server/proxy";

/** GET /api/bff/public/prices (`API-012`) */
export async function GET() {
  return proxyPublic("/api/v1/prices/public", "PRICES_UNAVAILABLE", "public, max-age=300, stale-while-revalidate=600");
}
