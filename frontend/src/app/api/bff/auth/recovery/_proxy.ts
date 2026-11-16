import { NextResponse } from "next/server";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/**
 * Forwards an account-recovery call to the backend. Recovery tokens travel only
 * in JSON bodies or the X-Recovery-Token header (never in URLs) and are not stored
 * server-side by the BFF. Errors return the backend's machine code.
 */
export async function forwardRecovery(path: string, init: { method: "GET" | "POST"; body?: unknown; recoveryToken?: string | null }) {
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    if (init.recoveryToken) headers["X-Recovery-Token"] = init.recoveryToken;
    const res = await fetch(`${backendInternalUrl}/api/v1${path}`, {
      method: init.method,
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const code =
        res.status === 429
          ? "RATE_LIMITED"
          : res.status === 422 && Array.isArray(data.detail)
            ? "INVALID_INPUT"
            : (typeof data.detail === "object" && data.detail?.code) || "RECOVERY_FAILED";
      return NextResponse.json({ ok: false, error: code }, { status: res.status });
    }
    return NextResponse.json({ ok: true, ...data }, { status: res.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ ok: false, error: "INTERNAL_ERROR" }, { status: 502 });
  }
}
