import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET() {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Profil ma'lumotlarini olish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const res = await fetch(`${backendInternalUrl}/api/v1/me/candidate`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Accept": "application/json",
      },
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { ok: false, error: data?.detail || data?.error || "PROFILE_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, profile: data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  if (!verifyCsrfOrigin(request)) {
    return NextResponse.json({ ok: false, error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
  }

  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Profilni yangilash uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const body = await request.json().catch(() => ({}));
    const changes: Record<string, unknown> = {};

    if (body.headline !== undefined) {
      const h = typeof body.headline === "string" ? body.headline.trim() : "";
      if (h.length < 1 || h.length > 200) {
        return NextResponse.json(
          { ok: false, error: "INVALID_HEADLINE", message: "headline 1 dan 200 belgigacha bo'lishi shart" },
          { status: 422 }
        );
      }
      changes.headline = h;
    }

    if (body.region !== undefined) {
      const r = typeof body.region === "string" ? body.region.trim() : "";
      if (r.length < 1 || r.length > 100) {
        return NextResponse.json(
          { ok: false, error: "INVALID_REGION", message: "region 1 dan 100 belgigacha bo'lishi shart" },
          { status: 422 }
        );
      }
      changes.region = r;
    }

    if (body.bio !== undefined) {
      changes.bio = typeof body.bio === "string" ? body.bio.trim() : null;
    }

    if (body.experience_months !== undefined) {
      const exp = Number(body.experience_months);
      if (isNaN(exp) || exp < 0 || exp > 1200) {
        return NextResponse.json(
          { ok: false, error: "INVALID_EXPERIENCE", message: "experience_months 0 dan 1200 oralig'ida bo'lishi shart" },
          { status: 422 }
        );
      }
      changes.experience_months = exp;
    }

    const res = await fetch(`${backendInternalUrl}/api/v1/me/candidate`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(changes),
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = typeof data?.detail === "string" ? data.detail : data?.error || "PROFILE_UPDATE_FAILED";
      return NextResponse.json({ ok: false, error: msg }, { status: res.status });
    }

    return NextResponse.json({ ok: true, contract_id: "API-026", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
