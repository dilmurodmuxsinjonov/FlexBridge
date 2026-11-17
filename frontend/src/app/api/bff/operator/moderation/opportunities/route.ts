import { proxyAuthed } from "@/lib/server/proxy";

/** Draft vacancies awaiting moderation (MODERATOR only; enforced by the backend). */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/moderation/opportunities?limit=100", { method: "GET", fallbackError: "MODERATION_QUEUE_FAILED" });
}
