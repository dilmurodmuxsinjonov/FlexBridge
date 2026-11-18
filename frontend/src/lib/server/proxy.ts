import { NextResponse } from "next/server";
import { backendFetch, getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

export const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Machine code from a FastAPI error body (AuthError/GovernanceError/validation). */
export function backendErrorCode(status: number, data: unknown, fallback: string): string {
  if (status === 429) return "RATE_LIMITED";
  const detail = (data as { detail?: unknown })?.detail;
  if (Array.isArray(detail)) return "INVALID_INPUT";
  if (detail && typeof detail === "object" && typeof (detail as { code?: unknown }).code === "string") {
    return (detail as { code: string }).code;
  }
  if (typeof detail === "string" && /^[A-Z0-9_]+$/.test(detail)) return detail;
  return fallback;
}

/**
 * Signed-in JSON proxy: CSRF origin check for writes, session token from the
 * encrypted cookie, backend error codes passed through as `{ ok:false, error }`.
 */
export async function proxyAuthed(
  request: Request,
  path: string,
  init: { method: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown; headers?: Record<string, string>; fallbackError: string }
): Promise<NextResponse> {
  if (init.method !== "GET" && !verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }
  const session = await getSessionFromCookie();
  if (!session?.access_token) {
    return NextResponse.json({ ok: false, error: "AUTH_REQUIRED" }, { status: 401 });
  }
  try {
    const headers: Record<string, string> = { Accept: "application/json", ...(init.headers || {}) };
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    const res = await backendFetch(
      path,
      { method: init.method, headers, body: init.body === undefined ? undefined : JSON.stringify(init.body) },
      session.access_token
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json({ ok: false, error: backendErrorCode(res.status, data, init.fallbackError) }, { status: res.status });
    }
    return NextResponse.json({ ok: true, ...data }, { status: res.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ ok: false, error: "INTERNAL_ERROR" }, { status: 502 });
  }
}

/**
 * Unauthenticated public JSON proxy: validates backend status cleanly and
 * normalizes error envelopes without exposing backend internals.
 */
export async function proxyPublic(
  path: string,
  fallbackError: string,
  cacheControl = "public, max-age=60, stale-while-revalidate=120"
): Promise<NextResponse> {
  try {
    const res = await backendFetch(path, { method: "GET" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: backendErrorCode(res.status, data, fallbackError) },
        { status: res.status }
      );
    }
    return NextResponse.json(
      { ok: true, ...data },
      { status: 200, headers: { "Cache-Control": cacheControl } }
    );
  } catch {
    return NextResponse.json({ ok: false, error: "BACKEND_UNAVAILABLE" }, { status: 503 });
  }
}
