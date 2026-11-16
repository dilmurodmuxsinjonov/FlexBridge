import { proxyAuthed } from "@/lib/server/proxy";

const FIELDS = ["tax_id", "legal_name", "public_name", "region", "description", "website", "file_ids", "evidence_note", "membership_role"] as const;

/**
 * POST /api/bff/employer/organizations — register a company (the founder becomes
 * its OWNER main account after platform review) or ask to join an existing one.
 */
export async function POST(request: Request) {
  const raw = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const body: Record<string, unknown> = {};
  for (const key of FIELDS) {
    if (raw[key] !== undefined && raw[key] !== null && raw[key] !== "") body[key] = raw[key];
  }
  return proxyAuthed(request, "/api/v1/organizations", { method: "POST", body, fallbackError: "ORGANIZATION_REGISTER_FAILED" });
}
