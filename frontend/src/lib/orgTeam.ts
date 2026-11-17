/**
 * Company main account (OWNER) & team (Issue #239). The founder registers the
 * company; after platform review they become its OWNER and manage staff:
 * invitations (shareable link), join requests, roles and removal.
 */
import { StaffApiError, describeStaffError } from "@/lib/universityStaff";

async function call<T>(url: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store", ...init });
  } catch {
    throw new StaffApiError("INTERNAL_ERROR", 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code =
      (typeof data?.error === "string" && data.error) ||
      (data?.detail && typeof data.detail === "object" && data.detail.code) ||
      "REQUEST_FAILED";
    throw new StaffApiError(String(code), res.status);
  }
  return data as T;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: JSON.stringify(body),
});

export type OrgRole = "OWNER" | "HR" | "HOST_COORDINATOR" | "MENTOR" | "BILLING";

export const ROLE_LABELS: Record<string, string> = {
  OWNER: "Rahbar (asosiy akkaunt)",
  HR: "HR mutaxassis",
  HOST_COORDINATOR: "Amaliyot koordinatori",
  MENTOR: "Mentor",
  BILLING: "Moliya / to‘lovlar",
};

export const ROLE_HINTS: Record<string, string> = {
  HR: "Vakansiya joylaydi, arizalarni ko‘radi, nomzodlarni qidiradi.",
  HOST_COORDINATOR: "Amaliyotchilarni qabul qiladi va amaliyot jarayonini boshqaradi.",
  MENTOR: "Biriktirilgan talabalarning kundaligini tasdiqlaydi.",
  BILLING: "Tariflar, to‘lovlar va kvotalarni boshqaradi.",
};

export interface TeamMember {
  membership_id: string;
  display_name: string;
  status: string;
  roles: string[];
  is_self: boolean;
  created_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  requested_role?: string | null;
  self_join?: boolean;
}

export interface TeamOverview {
  organization: { id: string; public_name: string; legal_name: string; status: string; tax_id: string; region: string };
  members: TeamMember[];
  join_requests: TeamMember[];
  invitations: Array<{ id: string; role_code: string | null; channel: string | null; created_at: string; expires_at: string }>;
}

export function fetchTeam(orgId: string) {
  return call<TeamOverview>(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/team`);
}

export function createInvitation(orgId: string, channel: "PHONE" | "EMAIL", destination: string, role: Exclude<OrgRole, "OWNER">) {
  return call<{ id: string; token: string; expires_at: string; role_code: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/invitations`,
    post({ channel, destination, role_code: role })
  );
}

export function revokeInvitation(orgId: string, id: string, reason: string) {
  return call(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/invitations/${encodeURIComponent(id)}/revoke`, post({ reason }));
}

export function approveJoin(orgId: string, membershipId: string) {
  return call(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/members/${encodeURIComponent(membershipId)}/approve`, post({}));
}

export function removeMember(orgId: string, membershipId: string, reason: string) {
  return call(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/memberships/${encodeURIComponent(membershipId)}/revoke`,
    post({ reason })
  );
}

export interface RegisterOrganizationBody {
  tax_id: string;
  legal_name: string;
  public_name: string;
  region: string;
  description?: string;
  website?: string;
  file_ids: string[];
  evidence_note: string;
  membership_role?: Exclude<OrgRole, "OWNER">;
}

export function registerOrganization(body: RegisterOrganizationBody) {
  return call<{ organization_id: string; membership_id: string; membership_status: string; case_id: string | null; created: boolean }>(
    "/api/bff/employer/organizations",
    post(body)
  );
}

export function invitationLink(token: string) {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `${origin}/korxona/royxatdan-otish?token=${encodeURIComponent(token)}`;
}

/** "+998 90 123-45-67" / "901234567" -> "+998901234567"; e-mail kept. */
export function normalizeDestination(raw: string): { channel: "PHONE" | "EMAIL"; destination: string } {
  const v = raw.trim();
  if (v.includes("@")) return { channel: "EMAIL", destination: v };
  let d = v.replace(/[\s()-]/g, "");
  if (/^[0-9]{9}$/.test(d)) d = "+998" + d;
  else if (/^998[0-9]{9}$/.test(d)) d = "+" + d;
  return { channel: "PHONE", destination: d };
}

const ORG_ERRORS: Record<string, string> = {
  SELF_INVITATION_FORBIDDEN: "O‘zingizni taklif qila olmaysiz.",
  INVITATION_ROLE_FORBIDDEN: "Bu rolga taklif qilib bo‘lmaydi.",
  INVITATION_ALREADY_ACCEPTED_USE_MEMBERSHIP_REVOKE: "Taklif allaqachon qabul qilingan — xodimni ro‘yxatdan olib tashlang.",
  INVITATION_NOT_AVAILABLE: "Taklif topilmadi yoki muddati tugagan. Rahbardan yangi havola so‘rang.",
  INVITATION_CONTACT_MISMATCH: "Taklif boshqa telefon/pochta uchun yuborilgan. Shu kontakt tasdiqlangan hisob bilan kiring.",
  INVITATION_BUSY_RETRY: "Birozdan so‘ng qayta urinib ko‘ring.",
  LAST_OWNER_PROTECTED: "Korxonaning yagona rahbarini olib tashlab bo‘lmaydi.",
  SELF_APPROVAL_FORBIDDEN: "O‘z so‘rovingizni o‘zingiz tasdiqlay olmaysiz.",
  MEMBERSHIP_NOT_PENDING: "Bu so‘rov allaqachon ko‘rib chiqilgan.",
  ORGANIZATION_NOT_VERIFIED: "Korxona hali tasdiqlanmagan — a’zolarni tasdiqlash tekshiruvdan keyin ochiladi.",
  ORG_SCOPE_FORBIDDEN: "Bu amal faqat korxona rahbariga (asosiy akkauntga) ruxsat etilgan.",
  MEMBERSHIP_REVIEW_REQUIRED: "Bu korxonadagi oldingi a’zoligingiz bekor qilingan. Rahbardan taklif so‘rang.",
  ORGANIZATION_NOT_AVAILABLE: "Bu STIR bilan korxona hozir ro‘yxatdan o‘tkazilmaydi.",
  INVALID_TAX_IDENTIFIER: "STIR noto‘g‘ri — faqat raqamlar (odatda 9 xonali).",
  EVIDENCE_NOT_CLEAN: "Hujjat hali tekshiruvdan o‘tmagan. Qayta yuklab ko‘ring.",
  INVALID_EVIDENCE_FILES: "Kamida bitta PDF hujjat biriktiring.",
};

export function describeOrgError(err: unknown): string {
  const code = err instanceof StaffApiError ? err.code : "";
  if (ORG_ERRORS[code]) return ORG_ERRORS[code];
  return describeStaffError(err); // shared governance/upload/MFA messages
}
