/**
 * University account & staff management (Issue #235): the university's own
 * coordinator account connects the institution and appoints its staff; every
 * appointment is reviewed by a platform moderator and accepted by the named
 * person before any role exists.
 */
export class StaffApiError extends Error {
  constructor(public code: string, public status: number) {
    super(code);
  }
}

async function call<T>(url: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store", ...init });
  } catch {
    throw new StaffApiError("INTERNAL_ERROR", 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new StaffApiError(String(data?.error || "REQUEST_FAILED"), res.status);
  return data as T;
}

const post = (body: unknown, headers: Record<string, string> = {}): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json", Accept: "application/json", ...headers },
  body: JSON.stringify(body),
});

export interface StaffAppointment {
  id: string;
  display_name: string;
  mode: "FIRST_COORDINATOR" | "STAFF_TEACHER";
  role: "COORDINATOR" | "TEACHER";
  is_self: boolean;
  status: string;
  case_status: string;
  decision_reason: string | null;
  revision: number;
  valid_from: string;
  valid_to: string | null;
  accepted_at: string | null;
  created_at: string;
  role_active: boolean;
}

export interface StaffOverview {
  institution: { id: string; name: string; status: string; registry_code: string };
  agreement: { id: string; version: number; status: string; valid_from: string; valid_to: string | null } | null;
  items: StaffAppointment[];
}

export interface VerifiedContact {
  id: string;
  channel: "PHONE" | "EMAIL";
  masked_destination: string;
  is_primary: boolean;
}

export function fetchStaff(institutionId: string) {
  return call<StaffOverview>(`/api/bff/university/institutions/${encodeURIComponent(institutionId)}/staff`);
}

export async function fetchMyVerifiedContacts(): Promise<VerifiedContact[]> {
  const data = await call<{ contacts?: VerifiedContact[] }>("/api/bff/university/appointments");
  return Array.isArray(data.contacts) ? data.contacts : [];
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(new StaffApiError("FILE_READ_FAILED", 0));
    reader.readAsDataURL(file);
  });
}

export const MAX_PDF_BYTES = 10 * 1024 * 1024;

export async function uploadStaffPdf(file: File, purpose: "INSTITUTION_APPOINTMENT" | "INSTITUTION_AGREEMENT") {
  if (file.type && file.type !== "application/pdf") throw new StaffApiError("INVALID_PDF_FORMAT", 0);
  if (file.size > MAX_PDF_BYTES) throw new StaffApiError("INVALID_FILE_SIZE", 0);
  const content_base64 = await fileToBase64(file);
  return call<{ file_id: string; filename: string }>("/api/bff/files/pdf", post({ filename: file.name, purpose, content_base64 }));
}

export interface AppointmentRequest {
  registry_code: string;
  document_file_id: string;
  contact_id: string;
  valid_from: string;
  valid_to?: string | null;
  legal_basis: string;
  file_ids: string[];
  evidence_note: string;
  // First coordinator (connecting a new university)
  name?: string;
  region?: string;
  agreement_file_id?: string;
  agreement_valid_from?: string;
  agreement_valid_to?: string | null;
  purposes?: ["ACADEMIC_VIEW"];
  // Staff request by an existing coordinator
  agreement_id?: string;
  target_channel?: "PHONE" | "EMAIL";
  target_destination?: string;
}

export function submitAppointment(body: AppointmentRequest, idempotencyKey: string) {
  return call<{ id: string; mode: string; status: string; case_status: string }>(
    "/api/bff/university/appointments",
    post(body, { "Idempotency-Key": idempotencyKey })
  );
}

export function revokeAppointment(id: string, reason: string) {
  return call<{ id: string; status: string }>(`/api/bff/university/appointments/${encodeURIComponent(id)}/revoke`, post({ reason }));
}

export interface RecoveryRequestItem {
  id: string;
  created_at: string;
  student_name: string;
  contacts: Array<{ channel: "PHONE" | "EMAIL"; masked: string }>;
}

export function fetchRecoveryRequests(institutionId: string) {
  return call<{ items: RecoveryRequestItem[]; approval_valid_hours: number }>(
    `/api/bff/university/institutions/${encodeURIComponent(institutionId)}/recovery-requests`
  );
}

export function decideRecoveryRequest(institutionId: string, id: string, decision: "APPROVE" | "REJECT", reason: string) {
  return call<{ id: string; status: string; valid_until: string | null }>(
    `/api/bff/university/institutions/${encodeURIComponent(institutionId)}/recovery-requests/${encodeURIComponent(id)}/decide`,
    post({ decision, reason })
  );
}

const STAFF_ERRORS: Record<string, string> = {
  RECOVERY_REQUEST_NOT_AVAILABLE: "Bu so‘rov endi mavjud emas yoki allaqachon ko‘rib chiqilgan.",
  RECOVERY_DECISION_REASON_REQUIRED: "Qanday tekshirganingizni kamida 15 belgida yozing.",
  MFA_REQUIRED: "Bu amal uchun ikki bosqichli himoya bilan kirgan bo‘lishingiz kerak. «Xavfsizlik» bo‘limida authenticator’ni yoqing, chiqib qayta kiring.",
  INSTITUTION_SCOPE_FORBIDDEN: "Bu amal faqat universitetning faol koordinatoriga ruxsat etilgan.",
  INSTITUTION_TARGET_UNAVAILABLE: "Bu telefon/pochta bilan tasdiqlangan FlexBridge hisobi topilmadi. Xodim avval ro‘yxatdan o‘tib, kontaktini tasdiqlashi kerak.",
  SELF_APPOINTMENT_FORBIDDEN: "O‘zingizni xodim sifatida qo‘sha olmaysiz.",
  INSTITUTION_AGREEMENT_NOT_CURRENT: "Universitetning amaldagi shartnomasi yo‘q yoki muddati tugagan.",
  INSTITUTION_AGREEMENT_NOT_FOUND: "Universitet shartnomasi topilmadi.",
  EXISTING_INSTITUTION_REQUIRES_STAFF_REQUEST: "Bu STIR bilan universitet allaqachon ulangan. Universitet koordinatoridan sizni xodim sifatida qo‘shishini so‘rang.",
  INSTITUTION_IDENTITY_REQUIRED: "Universitet nomi va hududini kiriting.",
  FIRST_INSTITUTION_AGREEMENT_REQUIRED: "Imzolangan hamkorlik shartnomasini (PDF) biriktiring.",
  INVALID_INSTITUTION_AGREEMENT: "Shartnoma sanalarini tekshiring: boshlanishi bugundan kech bo‘lmasin, tugashi bugundan oldin bo‘lmasin.",
  FIRST_COORDINATOR_MUST_BE_CURRENT: "Tayinlov boshlanish sanasi bugundan kech bo‘lmasligi kerak.",
  INVALID_APPOINTMENT_DATES: "Tayinlov sanalarini tekshiring.",
  INSTITUTION_LEGAL_BASIS_REQUIRED: "Huquqiy asosni kamida 15 belgida yozing (masalan, buyruq raqami va sanasi).",
  INSTITUTION_EVIDENCE_NOTE_REQUIRED: "Izohni kamida 15 belgida yozing.",
  INSTITUTION_REVOCATION_REASON_REQUIRED: "Bekor qilish sababini kamida 15 belgida yozing.",
  APPOINTMENT_DOCUMENT_NOT_IN_EVIDENCE: "Tayinlov hujjati biriktirilmagan.",
  EVIDENCE_NOT_CLEAN: "Hujjat hali tekshiruvdan o‘tmagan. Qayta yuklab ko‘ring.",
  EVIDENCE_ACCESS_DENIED: "Hujjatni qaytadan yuklang.",
  INVALID_CONTACT: "Telefon raqamni +998901234567 ko‘rinishida yoki to‘g‘ri pochta manzilini kiriting.",
  IDEMPOTENCY_CONFLICT: "Bu so‘rov allaqachon boshqa ma’lumot bilan yuborilgan. Sahifani yangilab qayta urinib ko‘ring.",
  INSTITUTION_BUSY_RETRY: "Universitet ma’lumotlari hozir yangilanmoqda. Birozdan so‘ng qayta urinib ko‘ring.",
  RATE_LIMITED: "Juda ko‘p urinish bo‘ldi. Birozdan so‘ng qayta urinib ko‘ring.",
  AUTH_REQUIRED: "Avval tizimga kiring.",
  INVALID_INPUT: "Majburiy maydonlar to‘liq emas yoki noto‘g‘ri.",
  INVALID_PDF_FORMAT: "Faqat PDF fayl qabul qilinadi.",
  INVALID_FILE_SIZE: "Fayl 10 MB dan oshmasligi kerak.",
  ANTIVIRUS_UNAVAILABLE: "Fayllarni tekshirish xizmati vaqtincha ishlamayapti. Birozdan so‘ng qayta urinib ko‘ring.",
  MALWARE_DETECTED_QUARANTINED: "Faylda xavfli kod aniqlandi — u qabul qilinmadi.",
  FILE_STORAGE_UNAVAILABLE: "Fayl omborida nosozlik. Birozdan so‘ng qayta urinib ko‘ring.",
  FILE_READ_FAILED: "Faylni o‘qib bo‘lmadi.",
  INTERNAL_ERROR: "Server bilan bog‘lanib bo‘lmadi.",
};

export function describeStaffError(err: unknown): string {
  const code = err instanceof StaffApiError ? err.code : err instanceof Error ? err.message : "";
  return STAFF_ERRORS[code] || "Amalni bajarib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.";
}

export const STATUS_LABELS: Record<string, string> = {
  PENDING_REVIEW: "Platforma tekshiruvida",
  APPROVED_PENDING_ACCEPT: "Xodim roziligi kutilmoqda",
  ACTIVE: "Faol",
  REVOKED: "Bekor qilingan",
  REJECTED: "Rad etilgan",
  NEEDS_INFO: "Qo‘shimcha ma’lumot so‘ralgan",
  DECLINED: "Xodim rad etgan",
  EXPIRED: "Muddati tugagan",
};

export function newIdempotencyKey(prefix: string) {
  const rand = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  return `${prefix}-${rand}`;
}
