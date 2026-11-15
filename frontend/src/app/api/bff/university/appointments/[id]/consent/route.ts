import { NextRequest, NextResponse } from "next/server";
import {
  backendFetch,
  getSessionFromCookie,
  setSessionCookie,
  verifyCsrfOrigin,
} from "@/lib/server/session";

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Tayinlovni tasdiqlash uchun tizimga kirish shart." },
      { status: 401 }
    );
  }

  const { id } = await context.params;
  if (!id || !UUID_REGEX.test(id)) {
    return NextResponse.json(
      { ok: false, error: "INVALID_APPOINTMENT_ID", message: "Tayinlov identifikatori noto‘g‘ri." },
      { status: 400 }
    );
  }

  try {
    const raw = (await request.json().catch(() => ({}))) as Record<string, unknown>;
    const decision = raw.decision === "DECLINE" ? "DECLINE" : "ACCEPT";
    const expectedRevision = Number(raw.expected_revision) || 1;
    const contactId = typeof raw.contact_id === "string" ? raw.contact_id.trim() : "";

    const backendPayload: {
      expected_revision: number;
      decision: "ACCEPT" | "DECLINE";
      contact_id?: string;
    } = {
      expected_revision: expectedRevision,
      decision,
    };
    if (decision === "ACCEPT" && contactId) {
      backendPayload.contact_id = contactId;
    }

    const res = await backendFetch(
      `/api/v1/institution-appointments/${encodeURIComponent(id)}/consent`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(backendPayload),
      },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: data?.detail?.code || data?.detail || data?.error || "APPOINTMENT_CONSENT_FAILED",
          message: "Tayinlov bo‘yicha rozilikni saqlab bo‘lmadi.",
        },
        { status: res.status }
      );
    }

    let updatedRoles = session.roles;
    const meRes = await backendFetch("/api/v1/auth/me", { method: "GET" }, session.access_token);
    if (meRes.ok) {
      const meData = await meRes.json().catch(() => null);
      if (meData && Array.isArray(meData.roles)) {
        updatedRoles = meData.roles;
        await setSessionCookie({
          token: session.access_token,
          user_id: String(meData.user_id || session.user_id),
          roles: updatedRoles,
          expires_at: session.expires_at,
        });
      }
    }

    return NextResponse.json({ ok: true, appointment: data, roles: updatedRoles }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR" },
      { status: 500 }
    );
  }
}
