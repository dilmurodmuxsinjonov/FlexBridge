import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(request: NextRequest) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Favqulodda kirish so'rovini yuborish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const targetUserId = body.target_user_id;
    const roleCode = body.role_code || "OPERATOR";
    const reason = typeof body.reason === "string" ? body.reason.trim() : "";
    const independentApproverId = body.independent_approver_id;
    const durationMinutes = Number(body.duration_minutes) || 120;

    if (!targetUserId || !independentApproverId) {
      return NextResponse.json(
        { error: "MISSING_REQUIRED_FIELDS", message: "target_user_id va independent_approver_id majburiy" },
        { status: 422 }
      );
    }

    if (!reason || reason.length < 5) {
      return NextResponse.json(
        { error: "INVALID_REASON", message: "Asos (reason) kamida 5 ta belgidan iborat bo'lishi shart" },
        { status: 422 }
      );
    }

    if (durationMinutes < 1 || durationMinutes > 240) {
      return NextResponse.json(
        { error: "INVALID_DURATION", message: "duration_minutes 1 dan 240 minutgacha (maksimal 4 soat) bo'lishi shart" },
        { status: 422 }
      );
    }

    const payload = {
      target_user_id: targetUserId,
      role_code: roleCode,
      reason,
      independent_approver_id: independentApproverId,
      duration_minutes: durationMinutes,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/operator/access-requests`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMessage =
        typeof data?.detail === "object" && data?.detail?.code
          ? data.detail.code
          : typeof data?.detail === "object" && data?.detail?.message
          ? data.detail.message
          : typeof data?.detail === "string"
          ? data.detail
          : data?.error || "ACCESS_REQUEST_FAILED";

      return NextResponse.json(
        { ok: false, error: errorMessage, message: data?.detail?.message || errorMessage },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, contract_id: "API-119", ...data }, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
