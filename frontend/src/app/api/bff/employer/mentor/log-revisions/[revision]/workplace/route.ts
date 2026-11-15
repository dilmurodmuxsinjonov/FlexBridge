import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ revision: string }> }
) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Kundalik tafsilotini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { revision } = await params;
    if (!revision) {
      return NextResponse.json(
        { ok: false, error: "REVISION_ID_REQUIRED", message: "Tahrir identifikatori ko'rsatilmagan." },
        { status: 400 }
      );
    }

    const backendRes = await backendFetch(
      `/api/v1/log-revisions/${encodeURIComponent(revision)}/workplace`,
      { method: "GET" },
      session.access_token
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorMessage =
        typeof data.detail === "object" && data.detail?.code
          ? data.detail.code
          : typeof data.detail === "string"
          ? data.detail
          : "FETCH_REVISION_DETAIL_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data.message || errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-091",
      revision: data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
