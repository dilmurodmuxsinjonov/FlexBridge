import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Operator kabinetiga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const startDate = searchParams.get("start_date");
    const endDate = searchParams.get("end_date");
    const cohort = searchParams.get("cohort");

    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    if (cohort) query.set("cohort", cohort);

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/operator/analytics?${query.toString()}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "FETCH_ANALYTICS_FAILED" },
        { status: backendRes.status }
      );
    }

    const dedupPct = data.analytics?.dedup_efficiency_pct ?? data.deduplication_effectiveness_pct ?? 100;
    const mutualRatePct = data.placements?.mutual_start_rate_pct ?? data.mutual_start_rate_pct ?? 0;
    const outboxPending = data.outbox_health?.pending_messages ?? data.outbox_backlog_count ?? 0;
    const totalEvents = data.analytics?.total_events ?? data.total_events_processed ?? 0;

    return NextResponse.json({
      ok: true,
      contract_id: "API-124",
      ...data,
      deduplication_effectiveness_pct: dedupPct,
      dedup_efficiency_pct: dedupPct,
      mutual_start_rate_pct: mutualRatePct,
      outbox_backlog_count: outboxPending,
      total_events_processed: totalEvents,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
