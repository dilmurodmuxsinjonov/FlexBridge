import { NextRequest, NextResponse } from "next/server";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * GET /api/bff/public/policies/[document] (API-014)
 * Public legal policies CMS proxy (CAP-039 / PUBLIC_INFO).
 * Available documents: terms, privacy, cookies, acceptable-use, rating-guidelines.
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ document: string }> }
) {
  try {
    const { document } = await context.params;
    if (!document) {
      return NextResponse.json(
        { ok: false, error: "MISSING_DOCUMENT", message: "Hujjat identifikatori kiritilishi shart." },
        { status: 400 }
      );
    }

    const backendRes = await fetch(`${backendInternalUrl}/api/v1/policies/${encodeURIComponent(document.toLowerCase())}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
      next: { revalidate: 600 },
    });

    const data = await backendRes.json().catch(() => ({}));

    if (!backendRes.ok) {
      const code = typeof data.detail === "object" ? (data.detail?.code || "POLICY_NOT_FOUND") : "POLICY_NOT_FOUND";
      const errMsg = typeof data.detail === "object" ? (data.detail?.message || code) : (data.detail || code);
      return NextResponse.json(
        { ok: false, code, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({
      ok: true,
      contract_id: "API-014",
      ...data,
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { ok: false, error: "BACKEND_UNAVAILABLE", message: err instanceof Error ? err.message : "Xizmat mavjud emas" },
      { status: 503 }
    );
  }
}
