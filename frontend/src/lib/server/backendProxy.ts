import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const BACKEND_INTERNAL_URL = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

/** Proxy an authenticated JSON request to FastAPI with CSRF check on mutating methods. */
export async function proxyBackendJson(
  request: NextRequest,
  backendPath: string,
  method: "GET" | "POST" | "PUT" | "DELETE" = "GET"
): Promise<NextResponse> {
  try {
    if (method !== "GET" && !verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const headers: Record<string, string> = {
      Authorization: `Bearer ${session.access_token}`,
      Accept: "application/json",
    };

    let body: string | undefined;
    if (method !== "GET" && method !== "DELETE") {
      const parsed = await request.json().catch(() => ({}));
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(parsed);
    }

    const res = await fetch(`${BACKEND_INTERNAL_URL}${backendPath}`, {
      method,
      headers,
      body,
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);
    if (!res.ok) {
      return NextResponse.json(data || { error: "BACKEND_REQUEST_FAILED" }, { status: res.status });
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/** Stream a binary document export (PDF/JSON) directly to the browser with Content-Disposition. */
export async function proxyBackendFileStream(backendPath: string): Promise<NextResponse> {
  try {
    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Hujjatni yuklab olish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const res = await fetch(`${BACKEND_INTERNAL_URL}${backendPath}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ error: "FILE_DOWNLOAD_FAILED" }));
      return NextResponse.json(errData, { status: res.status });
    }

    const buffer = await res.arrayBuffer();
    const contentType = res.headers.get("content-type") || "application/pdf";
    const disposition = res.headers.get("content-disposition") || 'attachment; filename="document.pdf"';

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": disposition,
        "Cache-Control": "no-store",
      },
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
