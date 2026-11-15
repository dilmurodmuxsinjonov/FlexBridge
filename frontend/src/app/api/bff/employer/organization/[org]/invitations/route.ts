import { NextRequest, NextResponse } from "next/server";
import { getSessionFromCookie, verifyCsrfOrigin } from "@/lib/server/session";

const backendInternalUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ org: string }> }
) {
  try {
    if (!verifyCsrfOrigin(request)) {
      return NextResponse.json({ error: "CSRF_ORIGIN_MISMATCH" }, { status: 403 });
    }

    const { org } = await params;
    if (!org || typeof org !== "string") {
      return NextResponse.json({ error: "INVALID_ORG_ID" }, { status: 400 });
    }

    const session = await getSessionFromCookie();
    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "AUTH_REQUIRED", message: "Taklifnoma yuborish uchun tizimga kirish talab etiladi." },
        { status: 401 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const channel = body.channel;
    const destination = typeof body.destination === "string" ? body.destination.trim() : "";
    const roleCode = body.role_code || body.role;

    if (!channel || !["EMAIL", "PHONE"].includes(String(channel).toUpperCase())) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "Yaroqsiz kanal (EMAIL yoki PHONE talab qilinadi)." },
        { status: 422 }
      );
    }
    if (destination.length < 3 || destination.length > 254) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "Manzil (telefon yoki email) 3 tadan 254 tagacha belgi bo'lishi shart." },
        { status: 422 }
      );
    }
    if (!roleCode || !["HR", "HOST_COORDINATOR", "MENTOR", "BILLING"].includes(String(roleCode))) {
      return NextResponse.json(
        { error: "VALIDATION_ERROR", message: "Ruxsat etilgan rollar: HR, HOST_COORDINATOR, MENTOR, BILLING." },
        { status: 422 }
      );
    }

    // Backend CreateInput has extra='forbid'
    const backendPayload = {
      channel: String(channel).toUpperCase(),
      destination,
      role_code: String(roleCode),
    };

    const res = await fetch(`${backendInternalUrl}/api/v1/organizations/${encodeURIComponent(org)}/invitations`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(backendPayload),
      cache: "no-store",
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      return NextResponse.json(
        data || { error: "INVITATION_FAILED" },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
