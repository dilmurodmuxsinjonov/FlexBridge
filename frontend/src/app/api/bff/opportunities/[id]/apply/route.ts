import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { id } = await params;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "INVALID_OPPORTUNITY_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Ariza topshirish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${session.access_token}`,
      "Content-Type": "application/json",
      "Accept": "application/json",
    };

    const idempotencyKey = request.headers.get("Idempotency-Key") || crypto.randomUUID();
    headers["Idempotency-Key"] = idempotencyKey;

    const res = await fetch(`${backendInternalUrl}/api/v1/opportunities/${encodeURIComponent(id)}/applications`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      if (res.status === 409) {
        return NextResponse.json(
          {
            ok: false,
            error: data?.detail?.code || "ALREADY_APPLIED",
            code: data?.detail?.code || "APPLICATION_ALREADY_EXISTS",
            message: data?.detail?.message || "Ushbu e'longa allaqachon faol ariza topshirilgan",
            detail: data?.detail,
            ...data,
          },
          { status: 409 }
        );
      }
      return NextResponse.json(
        data || { error: "APPLICATION_SUBMISSION_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
