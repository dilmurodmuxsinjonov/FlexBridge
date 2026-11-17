import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";
import { proxyAuthed } from "@/lib/server/proxy";

export async function GET() {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "OTM tayinlovlarini ko‘rish uchun tizimga kiring." },
      { status: 401 }
    );
  }

  try {
    const [inboxRes, optionsRes, contactsRes] = await Promise.all([
      backendFetch("/api/v1/me/institution-appointments", { method: "GET" }, session.access_token),
      backendFetch("/api/v1/institution-onboarding/options", { method: "GET" }, session.access_token),
      backendFetch("/api/v1/me/contacts", { method: "GET" }, session.access_token),
    ]);

    const inboxData = await inboxRes.json().catch(() => ({}));
    const optionsData = await optionsRes.json().catch(() => ({}));
    const contactsData = await contactsRes.json().catch(() => ({}));

    if (!inboxRes.ok) {
      return NextResponse.json(
        {
          ok: false,
          error: inboxData?.detail?.code || inboxData?.detail || inboxData?.error || "FETCH_FAILED",
          message: "OTM tayinlovlarini yuklashda xatolik yuz berdi.",
        },
        { status: inboxRes.status }
      );
    }

    return NextResponse.json(
      {
        ok: true,
        items: Array.isArray(inboxData?.items) ? inboxData.items : [],
        options: optionsRes.ok ? optionsData : null,
        contacts: contactsRes.ok && Array.isArray(contactsData?.items) ? contactsData.items : [],
      },
      { status: 200 }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR" },
      { status: 500 }
    );
  }
}

const APPOINTMENT_FIELDS = [
  "registry_code", "document_file_id", "contact_id", "valid_from", "valid_to", "legal_basis", "file_ids", "evidence_note",
  "name", "region", "agreement_id", "agreement_file_id", "agreement_valid_from", "agreement_valid_to", "purposes",
  "target_channel", "target_destination",
] as const;

/**
 * POST /api/bff/university/appointments — university connection request (first
 * coordinator) or a coordinator's staff request. Requires an MFA session; the
 * backend reviews it independently. Idempotency-Key comes from the client.
 */
export async function POST(request: Request) {
  const raw = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const body: Record<string, unknown> = {};
  for (const key of APPOINTMENT_FIELDS) {
    if (raw[key] !== undefined && raw[key] !== null && raw[key] !== "") body[key] = raw[key];
  }
  const key = request.headers.get("idempotency-key") || "";
  if (key.length < 8 || key.length > 128) {
    return NextResponse.json({ ok: false, error: "INVALID_IDEMPOTENCY_KEY" }, { status: 400 });
  }
  return proxyAuthed(request, "/api/v1/institution-appointments", {
    method: "POST",
    body,
    headers: { "Idempotency-Key": key },
    fallbackError: "APPOINTMENT_SUBMIT_FAILED",
  });
}
