import { NextRequest, NextResponse } from "next/server";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * GET /api/bff/auth/challenges/[id]/status
 * Checks current delivery and Telegram contact verification status of an auth challenge.
 */
export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await context.params;
    if (!id) {
      return NextResponse.json(
        { ok: false, error: "MISSING_CHALLENGE_ID" },
        { status: 400 }
      );
    }

    const backendRes = await fetch(
      `${backendInternalUrl}/api/v1/auth/challenges/${encodeURIComponent(id)}/status`,
      {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      }
    );

    const data = await backendRes.json().catch(() => ({}));
    if (!backendRes.ok) {
      const errMsg =
        typeof data.detail === "object"
          ? data.detail?.message || data.detail?.code
          : data.detail || "CHALLENGE_STATUS_FAILED";
      return NextResponse.json(
        { ok: false, error: errMsg, detail: data.detail },
        { status: backendRes.status }
      );
    }

    return NextResponse.json({ ok: true, ...data }, { status: 200 });
  } catch (err: unknown) {
    return NextResponse.json(
      {
        ok: false,
        error: "INTERNAL_ERROR",
        message: err instanceof Error ? err.message : "Xatolik yuz berdi",
      },
      { status: 500 }
    );
  }
}
