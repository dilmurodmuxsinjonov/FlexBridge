import { errorText } from "./errorText";

export interface ModerationVacancy {
  id: string;
  kind: string;
  capacity: number;
  created_at: string | null;
  title: string;
  description: string;
  contract_type: string | null;
  work_mode: string | null;
  region: string | null;
  is_paid: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_period: string | null;
  currency: string | null;
  organization_id: string;
  organization_name: string;
  organization_status: string;
  own: boolean;
}

const MESSAGES: Record<string, string> = {
  SELF_MODERATION_FORBIDDEN: "O‘zingiz yozgan e’lonni tasdiqlay olmaysiz.",
  MODERATION_STATE_CONFLICT: "Bu e’lon allaqachon ko‘rib chiqilgan. Ro‘yxatni yangilang.",
  MODERATION_JUSTIFICATION_REQUIRED: "Izoh kamida 15 belgidan iborat bo‘lsin.",
  FORBIDDEN_ROLE: "Bu bo‘lim faqat moderatorlar uchun.",
};

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...init, headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) }, cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code = typeof data?.error === "string" ? data.error : "";
    throw new Error(MESSAGES[code] || errorText(data, "MODERATION_FAILED"));
  }
  return data as T;
}

export const fetchModerationQueue = () =>
  call<{ items: ModerationVacancy[] }>("/api/bff/operator/moderation/opportunities").then((r) => r.items || []);

export const decideVacancy = (opportunity_id: string, action: "APPROVE" | "REJECT", reason_code: string, justification: string) =>
  call<{ ok: boolean }>("/api/bff/operator/moderation/actions", {
    method: "POST",
    body: JSON.stringify({ opportunity_id, action, reason_code, justification }),
  });

export const APPROVE_REASONS = [
  { code: "MEETS_POLICY", label: "Talablarga mos" },
  { code: "VERIFIED_EMPLOYER", label: "Tasdiqlangan korxona, ma’lumot to‘liq" },
];
export const REJECT_REASONS = [
  { code: "INCOMPLETE_INFO", label: "Ma’lumot yetarli emas" },
  { code: "MISLEADING_PAY", label: "To‘lov yoki shartlar noaniq" },
  { code: "LABOUR_LAW_CONFLICT", label: "Mehnat qonunchiligiga zid" },
  { code: "PROHIBITED_CONTENT", label: "Taqiqlangan mazmun" },
];
