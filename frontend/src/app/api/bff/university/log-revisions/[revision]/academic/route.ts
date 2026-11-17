import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ revision: string }> }
) {
  try {
    const { revision } = await params;
    if (!revision || typeof revision !== "string") {
      return NextResponse.json({ error: "INVALID_REVISION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Kundalik ma'lumotlarini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/log-revisions/${encodeURIComponent(revision)}/academic`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "FETCH_REVISION_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
