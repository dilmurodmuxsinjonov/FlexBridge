import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Taqsimot navbatini ko'rish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    let institutionId = searchParams.get("institution_id");
    const limit = searchParams.get("limit") || "50";
    const after = searchParams.get("after");

    // Auto-discover institution if omitted
    if (!institutionId) {
      const meRes = await fetch(`${backendInternalUrl}/api/v1/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (meRes.ok) {
        const meData = await meRes.json();
        // check institutions or scopes in meData
        if (Array.isArray(meData.institutions) && meData.institutions.length > 0) {
          institutionId = meData.institutions[0].id || meData.institutions[0].institution_id;
        } else if (Array.isArray(meData.memberships)) {
          const instMem = meData.memberships.find((m: { institution_id?: string }) => m.institution_id);
          if (instMem) institutionId = instMem.institution_id;
        }
      }
    }

    if (!institutionId) {
      return NextResponse.json(
        { ok: false, error: "INSTITUTION_REQUIRED", message: "Muassasa identifikatori topilmadi yoki ko'rsatilmagan." },
        { status: 400 }
      );
    }

    const query = new URLSearchParams({ limit });
    if (after) query.set("after", after);

    const [queueRes, teachersRes] = await Promise.all([
      fetch(`${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/assignment-queue?${query.toString()}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      }),
      fetch(`${backendInternalUrl}/api/v1/institutions/${encodeURIComponent(institutionId)}/academic-teachers?limit=100`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      }),
    ]);

    const queueData = await queueRes.json().catch(() => ({}));
    const teachersData = await teachersRes.json().catch(() => ({}));

    if (!queueRes.ok) {
      return NextResponse.json(
        { ok: false, error: queueData.detail || "FETCH_QUEUE_FAILED" },
        { status: queueRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-103",
      institution_id: institutionId,
      items: Array.isArray(queueData.items) ? queueData.items : [],
      teachers: Array.isArray(teachersData.items) ? teachersData.items : [],
      next_after: queueData.next_after || null,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
