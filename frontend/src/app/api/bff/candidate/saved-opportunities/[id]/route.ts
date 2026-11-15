import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_SAVED_OPPORTUNITY_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Saqlangan e'lonni o'chirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/me/saved-opportunities/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    if (res.status === 204 || res.ok) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await res.json().catch(() => null);
    return NextResponse.json(
      data || { error: "DELETE_SAVED_OPPORTUNITY_FAILED" },
      { status: res.status }
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
