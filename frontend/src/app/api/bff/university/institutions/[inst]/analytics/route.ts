import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ inst: string }> }
) {
  try {
    // If request contains an Origin header, ensure CSRF origin protection matches
    if (request.headers.get("origin") && !verifyCsrfOrigin(request)) {
      return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { inst: institutionId } = await params;
    if (!institutionId) {
      return NextResponse.json({ ok: false, error: "INVALID_INSTITUTION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Universitet analitikasini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const program = searchParams.get("program");
    const organization_id = searchParams.get("organization_id");
    const status = searchParams.get("status");
    const from_date = searchParams.get("from_date");
    const to_date = searchParams.get("to_date");

    const query = new URLSearchParams();
    if (program) query.set("program", program);
    if (organization_id) query.set("organization_id", organization_id);
    if (status) query.set("status", status);
    if (from_date) query.set("from_date", from_date);
    if (to_date) query.set("to_date", to_date);

    const queryString = query.toString() ? `?${query.toString()}` : "";
    const backendRes = await fetch(`${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/analytics${queryString}`, {
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
        { ok: false, error: data.detail || "FETCH_ANALYTICS_FAILED", message: data.message },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-125",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
