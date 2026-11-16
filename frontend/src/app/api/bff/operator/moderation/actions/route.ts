import { proxyAuthed } from "@/lib/server/proxy";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Approve or reject a draft vacancy. Only the fields the backend accepts are forwarded. */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const id = String(body.opportunity_id || "");
  const action = body.action === "REJECT" ? "REJECT" : body.action === "APPROVE" ? "APPROVE" : "";
  const justification = typeof body.justification === "string" ? body.justification.trim().slice(0, 2000) : "";
  const reason = typeof body.reason_code === "string" ? body.reason_code.trim().slice(0, 80) : "";
  if (!UUID_RE.test(id) || !action || justification.length < 15 || !reason) {
    return Response.json({ ok: false, error: "INVALID_INPUT" }, { status: 422 });
  }
  return proxyAuthed(request, "/api/v1/moderation/actions", {
    method: "POST",
    body: {
      target_entity_type: "opportunity",
      target_entity_id: id,
      action_type: action,
      policy_code: "VACANCY_CONTENT_POLICY",
      reason_code: reason,
      justification,
    },
    fallbackError: "MODERATION_ACTION_FAILED",
  });
}
