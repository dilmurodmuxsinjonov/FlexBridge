import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Nomzod arizalari ro'yxatini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const forwardParams = new URLSearchParams();

    const status = searchParams.get("status");
    if (status) forwardParams.set("status", status);

    const limit = searchParams.get("limit");
    if (limit) forwardParams.set("limit", limit);

    const after = searchParams.get("after");
    if (after) forwardParams.set("after", after);

    const queryString = forwardParams.toString();
    const endpoint = `${backendInternalUrl}/api/v1/me/applications${queryString ? `?${queryString}` : ""}`;

    const res = await fetch(endpoint, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "CANDIDATE_APPLICATIONS_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
