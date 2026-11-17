import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; date: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const { id, date } = await params;
    if (!id || typeof id !== "string" || !date || typeof date !== "string") {
      return NextResponse.json({ error: "INVALID_PLACEMENT_OR_DATE" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Kundalikni saqlash uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const dayType = body.day_type || "WORKED";
    const summaryText = body.summary_text || body.summary || "";
    const tasks = Array.isArray(body.tasks) ? body.tasks : [];
    const totalMinutes = typeof body.total_minutes === "number"
      ? body.total_minutes
      : tasks.reduce((sum: number, t: { minutes?: number }) => sum + (t.minutes || 0), 0);

    const taskMinutesSum = tasks.reduce((sum: number, t: { minutes?: number }) => sum + (Number(t.minutes) || 0), 0);
    if (tasks.length > 0 && typeof body.total_minutes === "number" && taskMinutesSum !== body.total_minutes) {
      return NextResponse.json(
        { error: "TASK_MINUTES_MISMATCH", message: "Vazifalar daqiqalari yig'indisi umumiy vaqtga teng bo'lishi shart." },
        { status: 422 }
      );
    }

    const payload = {
      day_type: dayType,
      summary_text: summaryText,
      total_minutes: totalMinutes,
      tasks: tasks.map((t: { title?: string; minutes?: number; start_minute?: number; end_minute?: number }) => ({
        title: t.title || "Amaliyot vazifasi",
        minutes: typeof t.minutes === "number" ? t.minutes : 60,
        start_minute: t.start_minute,
        end_minute: t.end_minute,
      })),
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/placements/${encodeURIComponent(id)}/logs/${encodeURIComponent(date)}`, {
      method: "PUT",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "SAVE_DRAFT_LOG_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
