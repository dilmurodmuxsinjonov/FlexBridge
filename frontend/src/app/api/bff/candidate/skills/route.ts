import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie();
  if (!session || !session.access_token) {
    return NextResponse.json(
      { ok: false, error: "AUTH_REQUIRED", message: "Ko'nikmalar katalogini ko'rish uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const { searchParams } = new URL(request.url);
    const q = searchParams.get("q") || "";
    const limit = searchParams.get("limit") || "50";

    const sp = new URLSearchParams();
    if (q) sp.set("q", q);
    sp.set("limit", limit);

    const res = await fetch(`${backendInternalUrl}/api/v1/skills?${sp.toString()}`, {
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
        { ok: false, error: data?.detail || data?.error || "SKILLS_FETCH_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json({ ok: true, items: data.items || [] }, { status: 200 });
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
      { ok: false, error: "AUTH_REQUIRED", message: "Ko'nikmalarni yangilash uchun tizimga kirish talab etiladi." },
      { status: 401 }
    );
  }

  try {
    const body = await request.json().catch(() => ({}));
    const skills = Array.isArray(body.skills) ? body.skills : [];
    const removeSkillIds = Array.isArray(body.remove_skill_ids) ? body.remove_skill_ids : [];

    const payload = {
      skills: skills.map((s: { skill_id: string; level: string }) => ({
        skill_id: String(s.skill_id),
        level: String(s.level || "BEGINNER"),
      })),
      remove_skill_ids: removeSkillIds.map((id: string) => String(id)),
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/me/candidate/skills`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = typeof data?.detail === "string" ? data.detail : data?.error || "SKILLS_UPDATE_FAILED";
      return NextResponse.json({ ok: false, error: msg }, { status: res.status });
    }

    return NextResponse.json({ ok: true, contract_id: "API-032", ...data }, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "INTERNAL_SERVER_ERROR";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
