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
    const provider = searchParams.get("provider");
    const discrepancyOnly = searchParams.get("discrepancy_only");
    const limit = searchParams.get("limit") || "50";
    const cursor = searchParams.get("cursor");

    const query = new URLSearchParams({ limit });
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    if (provider) query.set("provider", provider);
    if (discrepancyOnly) query.set("discrepancy_only", discrepancyOnly);
    if (cursor) query.set("cursor", cursor);

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/operator/reconciliation?${query.toString()}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || data.detail?.code) : (data.detail || "FETCH_RECONCILIATION_FAILED");
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-115",
      items: Array.isArray(data.items) ? data.items : (Array.isArray(data) ? data : []),
      summary: data.summary,
      next_cursor: data.next_cursor || null,
      total_records: data.total_records,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
