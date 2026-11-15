import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie } from "@/lib/server/session";

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
