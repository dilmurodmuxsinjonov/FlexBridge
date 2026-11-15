import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ inst: string }> }
) {
  try {
    const { inst: institutionId } = await params;
    if (!institutionId) {
      return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Talabalar nazorat ro'yxatini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    const after = searchParams.get("after");

    const query = new URLSearchParams({ limit });
    if (after) query.set("after", after);

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/supervisions?${query.toString()}`, {
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
        { ok: false, error: data.detail || "FETCH_SUPERVISIONS_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-098",
      institution_id: institutionId,
      items: Array.isArray(data.items) ? data.items : [],
      next_after: data.next_after || null,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
