import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/session";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ token: string }> }
) {
  const { token } = await context.params;
  if (!token || !/^[A-Za-z0-9_-]{43}$/.test(token)) {
    return NextResponse.json(
      { ok: false, error: "INVALID_INVITATION_TOKEN", message: "Taklif tokeni formati noto‘g‘ri." },
      { status: 400 }
    );
  }

  try {
    const res = await backendFetch(`/api/v1/invitations/${encodeURIComponent(token)}`, {
      method: "GET",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: data?.detail?.code || data?.detail || data?.error || "INVITATION_NOT_FOUND",
          message: "Taklif topilmadi yoki muddati tugagan.",
        },
        { status: res.status }
      );
    }
    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR" },
      { status: 500 }
    );
  }
}
