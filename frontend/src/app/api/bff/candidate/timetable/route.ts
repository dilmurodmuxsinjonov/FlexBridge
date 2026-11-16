import { proxyAuthed } from "@/lib/server/proxy";

/** The signed-in student's own class timetable (read-only). */
export async function GET(request: Request) {
  return proxyAuthed(request, "/api/v1/me/timetable", { method: "GET", fallbackError: "TIMETABLE_FETCH_FAILED" });
}
