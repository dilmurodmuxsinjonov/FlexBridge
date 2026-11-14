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
      return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { id: placementId } = await params;
    if (!placementId) {
      return NextResponse.json({ ok: false, error: "INVALID_PLACEMENT_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { ok: false, error: "AUTH_REQUIRED", message: "Akademik xulosa berish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const decision = body.decision;
    if (decision !== "ACADEMIC_REVIEW_COMPLETE" && decision !== "ACADEMIC_REVISION_REQUIRED") {
      return NextResponse.json(
        { ok: false, error: "INVALID_DECISION", message: "Qaror 'ACADEMIC_REVIEW_COMPLETE' yoki 'ACADEMIC_REVISION_REQUIRED' bo'lishi shart." },
        { status: 422 }
      );
    }

    const reason = typeof body.reason === "string" ? body.reason.trim() : "";
    if (reason.length < 1 || reason.length > 2000) {
      return NextResponse.json(
        { ok: false, error: "INVALID_REASON", message: "Xulosa asosi 1 dan 2000 belgigacha bo'lishi shart." },
        { status: 422 }
      );
    }

    let academicAssignmentId = body.academic_assignment_id;
    let termsId = body.terms_id;
    let version = body.version;
    let expectedBasisDigest = body.expected_basis_digest;

    // Auto-resolve context fields if omitted by UI
    if (!academicAssignmentId || !termsId || !version || !expectedBasisDigest) {
      // 1. Resolve assignment ID
      if (!academicAssignmentId) {
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
          if (found) academicAssignmentId = found.id;
        }
      }

      if (!academicAssignmentId) {
        return NextResponse.json(
          { ok: false, error: "ASSIGNMENT_NOT_FOUND", message: "Ushbu amaliyot uchun o'qituvchi biriktiruvi topilmadi." },
          { status: 404 }
        );
      }

      // 2. Fetch context from backend
      const ctxRes = await fetch(
        `${backendInternalUrl}/api/v1/placements/${encodeURIComponent(placementId)}/academic-decision-context?academic_assignment_id=${encodeURIComponent(academicAssignmentId)}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            Accept: "application/json",
          },
          cache: "no-store",
        }
      );

      if (!ctxRes.ok) {
        const ctxErr = await ctxRes.json().catch(() => ({}));
        return NextResponse.json(
          { ok: false, error: ctxErr.detail || "FETCH_CONTEXT_FAILED" },
          { status: ctxRes.status }
        );
      }

      const ctxData = await ctxRes.json();
      termsId = ctxData.terms_id;
      version = ctxData.version;
      expectedBasisDigest = ctxData.basis_digest;
    }

    const idempotencyKey =
      (typeof body.idempotency_key === "string" && body.idempotency_key.length >= 8)
        ? body.idempotency_key
        : (request.headers.get("Idempotency-Key") || `flx-conclude-${crypto.randomUUID()}`);

    const backendPayload = {
      academic_assignment_id: academicAssignmentId,
      terms_id: termsId,
      version: Number(version),
      expected_basis_digest: expectedBasisDigest,
      decision,
      reason,
      idempotency_key: idempotencyKey,
    };

    const backendRes = await fetch(
      `${backendInternalUrl}/api/v1/placements/${encodeURIComponent(placementId)}/academic-decisions`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(backendPayload),
        cache: "no-store",
      }
    );

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      return NextResponse.json(
        { ok: false, error: data.detail || "CONCLUDE_FAILED" },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-108",
      receipt: data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
