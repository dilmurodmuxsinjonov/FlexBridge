import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ revision: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { revision } = await params;
    if (!revision || typeof revision !== "string") {
      return NextResponse.json({ error: "INVALID_REVISION_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Kundalikni baholash uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const decision = body.decision;
    if (decision !== "REVIEWED" && decision !== "NEEDS_REVISION") {
      return NextResponse.json(
        { error: "INVALID_REVIEW_DECISION", message: "Qaror faqat 'REVIEWED' yoki 'NEEDS_REVISION' bo'lishi mumkin." },
        { status: 422 }
      );
    }

    let academicAssignmentId = body.academic_assignment_id;

    // Auto-resolve academic_assignment_id if omitted by client
    if (!academicAssignmentId) {
      const revisionRes = await fetch(`${backendInternalUrl}/api/v1/log-revisions/${encodeURIComponent(revision)}/academic`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!revisionRes.ok) {
        const revErr = await revisionRes.json().catch(() => ({}));
        return NextResponse.json(
          revErr || { error: "FETCH_REVISION_FAILED" },
          { status: revisionRes.status }
        );
      }

      const revData = await revisionRes.json();
      const placementId = revData.placement_id;

      // Fetch teacher's active assignments
      const assignmentsRes = await fetch(`${backendInternalUrl}/api/v1/me/academic-assignments?limit=100`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!assignmentsRes.ok) {
        return NextResponse.json(
          { error: "FETCH_ASSIGNMENTS_FAILED", message: "O'qituvchi tayinlovlarini tekshirib bo'lmadi." },
          { status: assignmentsRes.status }
        );
      }

      const assignmentsData = await assignmentsRes.json();
      const matchingAssignment = Array.isArray(assignmentsData.items)
        ? assignmentsData.items.find((a: { placement_id: string }) => a.placement_id === placementId)
        : null;

      if (!matchingAssignment || !matchingAssignment.id) {
        return NextResponse.json(
          { error: "TEACHER_ASSIGNMENT_NOT_FOUND", message: "Ushbu stajirovka bo'yicha o'qituvchi tayinlovi topilmadi." },
          { status: 403 }
        );
      }

      academicAssignmentId = matchingAssignment.id;
    }

    const idempotencyKey =
      typeof body.idempotency_key === "string" && body.idempotency_key.length >= 8
        ? body.idempotency_key
        : `rev-${crypto.randomUUID()}`;

    const backendPayload = {
      academic_assignment_id: academicAssignmentId,
      decision: decision,
      comment: typeof body.comment === "string" ? body.comment : "",
      idempotency_key: idempotencyKey,
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/log-revisions/${encodeURIComponent(revision)}/academic-reviews`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(backendPayload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "SUBMIT_ACADEMIC_REVIEW_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
