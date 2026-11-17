import { NextRequest, NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        {
          ok: false,
          error: "AUTH_REQUIRED",
          message: "Nomzodlarni qidirish uchun tizimga kirish talab etiladi.",
        },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    const qs = searchParams.toString();
    const endpoint = `/api/v1/employer/candidates/search${qs ? `?${qs}` : ""}`;

    const backendRes = await backendFetch(endpoint, { method: "GET" }, session.access_token);
    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const errorCode =
        typeof data.detail === "object" && data.detail?.code
          ? data.detail.code
          : typeof data.detail === "string"
          ? data.detail
          : "SEARCH_CANDIDATES_FAILED";

      const errorMessage =
        typeof data.detail === "object" && data.detail?.message
          ? data.detail.message
          : typeof data.message === "string"
          ? data.message
          : errorCode;

      return NextResponse.json(
        { ok: false, error: errorCode, message: errorMessage },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      {
        ok: false,
        error: "BACKEND_UNAVAILABLE",
        message: err instanceof Error ? err.message : "Xizmat vaqtincha mavjud emas",
      },
      { status: 503 }
    );
  }
}
