import { NextRequest, NextResponse } from "next/server";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * GET /api/bff/public/help/[document] (API-013)
 * Public versioned help & FAQ documentation CMS proxy (CAP-039 / PUBLIC_INFO).
 * Available documents: onboarding, candidate-guide, employer-guide, academic-guide, schedule-matching.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ document: string }> }
) {
  try {
    const { document } = await context.params;
    if (!document) {
      return NextResponse.json(
        { ok: false, error: "MISSING_DOCUMENT", message: "Qo'llanma identifikatori kiritilishi shart." },
        { status: 400 }
      );
    }

    const rawDoc = document.toLowerCase();
    const targetDoc = rawDoc === "onboarding" ? "getting-started" : rawDoc;

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/help/${encodeURIComponent(targetDoc)}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      next: { revalidate: 600 },
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const code = typeof data.detail === "object" ? (data.detail?.code || "DOCUMENT_NOT_FOUND") : "DOCUMENT_NOT_FOUND";
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || code) : (data.detail || code);
      return NextResponse.json(
        { ok: false, code, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-013",
      document: document.toLowerCase(),
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
