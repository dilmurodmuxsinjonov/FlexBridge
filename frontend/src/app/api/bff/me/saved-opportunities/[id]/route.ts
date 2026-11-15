import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

function verifyOrigin(req: NextRequest): boolean {
  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (!origin || !host) return true;
  try {
    const originHost = new URL(origin).host;
    return originHost === host;
  } catch {
    return false;
  }
}

export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  if (!verifyOrigin(req)) {
    return NextResponse.json(
      { ok: false, error: "CSRF_ORIGIN_MISMATCH", message: "Xavfsizlik tekshiruvidan o'tmadi" },
      { status: 403 }
    );
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Tizimga kirish talab etiladi" },
      { status: 401 }
    );
  }

  const { id } = await context.params;

  try {
    const res = await fetch(`${BACKEND_INTERNAL_URL}/api/v1/me/saved-opportunities/${id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        Accept: "application/json",
      },
    });

    if (!res.ok && res.status !== 204) {
      const data = await res.json().catch(() => ({}));
      return NextResponse.json(
        { ok: false, error: data?.detail?.code || "UNSAVE_FAILED", message: data?.detail?.message || "Saqlangan e'lonni o'chirib bo'lmadi" },
        { status: res.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-038",
      deleted_id: id,
    });
  } catch (err: any) {
    return NextResponse.json(
      { ok: false, error: "PROXY_ERROR", message: err?.message || "Ichki tarmoq xatoligi" },
      { status: 502 }
    );
  }
}
