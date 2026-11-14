import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: placementId } = await params;
    if (!placementId) {
      return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Xulosa kontekstini olish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const { searchParams } = new URL(request.url);
    let assignmentId = searchParams.get("academic_assignment_id");

    // Auto-resolve assignmentId for the placement if omitted
    if (!assignmentId) {
      const assignmentsRes = await fetch(`${backendInternalUrl}/api/v1/me/academic-assignments?limit=100`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (assignmentsRes.ok) {
        const assignData = await assignmentsRes.json();
        const found = assignData.items?.find((a: { placement_id: string }) => a.placement_id === placementId);
        if (found) {
          assignmentId = found.id;
        }
      }
    }

    if (!assignmentId) {
      return NextResponse.json(
        { ok: false, error: "ASSIGNMENT_NOT_FOUND", message: "Ushbu amaliyot uchun o'qituvchi biriktiruvi topilmadi." },
        { status: 404 }
      );
    }

    const backendRes = await fetch(
      `${backendInternalUrl}/api/v1/placements/${encodeURIComponent(placementId)}/academic-decision-context?academic_assignment_id=${encodeURIComponent(assignmentId)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      }
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "FETCH_CONTEXT_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-108-CONTEXT",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
