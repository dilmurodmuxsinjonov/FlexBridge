import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";
import { proxyJsonBody } from "@/lib/server/proxy";

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Tashkilot amaliyotlarini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const orgId = searchParams.get("organization_id");
    const limit = searchParams.get("limit") || "50";
    const after = searchParams.get("after");

    if (!orgId) {
      return NextResponse.json(
        { ok: false, error: "ORGANIZATION_ID_REQUIRED", message: "Tashkilot identifikatori ko'rsatilmagan." },
        { status: 400 }
      );
    }

    const qs = new URLSearchParams({ limit });
    if (after) qs.set("after", after);

    const backendRes = await backendFetch(
      `/api/v1/organizations/${encodeURIComponent(orgId)}/placements?${qs.toString()}`,
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
          : "FETCH_ORG_PLACEMENTS_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data.message || errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-069",
      items: data.items || [],
      next_after: data.next_after || null,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}

export async function POST(request: Request) {
  return proxyJsonBody(request, "/api/v1/placements", "POST", "CREATE_PLACEMENT_FAILED");
}
