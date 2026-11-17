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

    // Auto-discover the coordinator's institution from GET /me/workspaces.
    if (!institutionId) {
      const wsRes = await fetch(`${backendInternalUrl}/api/v1/me/workspaces`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });
      if (wsRes.ok) {
        const ws = await wsRes.json();
        const institutions: Array<{ id: string; roles?: string[] }> = Array.isArray(ws.institutions) ? ws.institutions : [];
        const coordinated = institutions.find((i) => (i.roles || []).includes("COORDINATOR"));
        institutionId = (coordinated ?? institutions[0])?.id ?? null;
      }
    }

    if (!institutionId) {
      // Not attached to any institution yet: an empty queue, not an error.
      return NextResponse.json({ ok: true, contract_id: "API-103", institution_id: null, items: [], teachers: [], has_more: false });
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
