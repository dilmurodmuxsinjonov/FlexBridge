/**
 * Turns any BFF/backend error body into one short Uzbek sentence.
 *
 * BFF routes return `{ error, message }`, where `error` may be a machine code,
 * the backend's `detail` object (`{code, message}`) or a string. Before this,
 * objects were stringified to "[object Object]" and codes such as
 * INSTITUTIONS_NOT_FOUND were shown to people as-is.
 */

const GENERIC = "Amalni bajarib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.";

const MESSAGES: Record<string, string> = {
  AUTH_REQUIRED: "Tizimga kirish talab etiladi. Iltimos, qaytadan kiring.",
  AUTH_REVOKED: "Sessiya tugagan. Iltimos, qaytadan kiring.",
  SESSION_EXPIRED: "Sessiya muddati tugagan. Iltimos, qaytadan kiring.",
  MFA_REQUIRED: "Bu amal uchun ikki bosqichli himoya bilan kirgan bo‘lishingiz kerak.",
  MFA_ENROLLMENT_REQUIRED: "Avval «Xavfsizlik» bo‘limida ikki bosqichli himoyani yoqing.",
  RATE_LIMITED: "Juda ko‘p urinish bo‘ldi. Birozdan so‘ng qayta urinib ko‘ring.",
  CSRF_ORIGIN_MISMATCH: "So‘rov boshqa manzildan yuborildi. Sahifani yangilab, qayta urinib ko‘ring.",
  INTERNAL_ERROR: "Server bilan bog‘lanib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.",
  INTERNAL_SERVER_ERROR: "Server bilan bog‘lanib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.",
  INSTITUTIONS_NOT_FOUND: "Universitet topilmadi yoki siz uning xodimi emassiz.",
  INSTITUTION_NOT_FOUND: "Universitet topilmadi.",
  INSTITUTION_SCOPE_FORBIDDEN: "Bu bo‘lim faqat universitet xodimlariga ochiq.",
  ORG_SCOPE_FORBIDDEN: "Bu bo‘lim faqat korxona xodimlariga ochiq.",
  ORGANIZATION_NOT_VERIFIED: "Korxona hali tasdiqlanmagan.",
  CANDIDATE_PROFILE_REQUIRED: "Bu bo‘lim talaba (nomzod) hisobi uchun.",
  ROLE_PORTAL_MISMATCH: "Hisobingiz bu bo‘limga kirish huquqiga ega emas.",
  INVALID_INPUT: "Kiritilgan ma’lumotlar to‘liq emas yoki noto‘g‘ri.",
  ANTIVIRUS_UNAVAILABLE: "Fayllarni tekshirish xizmati vaqtincha ishlamayapti.",
  MALWARE_DETECTED_QUARANTINED: "Faylda xavfli kod aniqlandi — u qabul qilinmadi.",
  FILE_STORAGE_UNAVAILABLE: "Fayl omborida nosozlik. Birozdan so‘ng qayta urinib ko‘ring.",
  INVALID_PDF_FORMAT: "Faqat PDF fayl qabul qilinadi.",
  INVALID_FILE_SIZE: "Fayl hajmi juda katta.",
  ENTITLEMENT_REQUIRED: "Bu amal uchun tarif yoki kvota kerak.",
  QUOTA_EXCEEDED: "Kvota tugagan. Tarifni yangilang.",
};

const isCode = (s: string) => /^[A-Z][A-Z0-9_]{2,}$/.test(s.trim());

function byPattern(code: string): string | null {
  if (MESSAGES[code]) return MESSAGES[code];
  if (/_NOT_FOUND$/.test(code)) return "Ma’lumot topilmadi.";
  if (/(_FORBIDDEN|_DENIED)$/.test(code)) return "Bu amal uchun ruxsatingiz yo‘q.";
  if (/^INVALID_|_INVALID$/.test(code)) return "Kiritilgan ma’lumotlarni tekshiring.";
  if (/_REQUIRED$/.test(code)) return "Majburiy ma’lumot yetishmayapti.";
  if (/_UNAVAILABLE$/.test(code)) return "Xizmat vaqtincha ishlamayapti. Birozdan so‘ng qayta urinib ko‘ring.";
  if (/(_CONFLICT|_BUSY|_BUSY_RETRY|_CHANGED)$/.test(code)) return "Ma’lumot boshqa joyda o‘zgargan. Sahifani yangilab, qayta urinib ko‘ring.";
  return null;
}

function pick(v: unknown): { code?: string; text?: string } {
  if (typeof v === "string") return isCode(v) ? { code: v.trim() } : { text: v };
  if (v && typeof v === "object") {
    const o = v as { code?: unknown; message?: unknown };
    return { code: typeof o.code === "string" ? o.code : undefined };
  }
  return {};
}

export function errorText(data: unknown, fallback: string): string {
  const d = (data && typeof data === "object" ? data : {}) as Record<string, unknown>;
  const message = typeof d.message === "string" && d.message.trim() && !isCode(d.message) ? d.message.trim() : null;
  const fromError = pick(d.error);
  const fromDetail = pick(d.detail);
  const code = fromError.code || fromDetail.code || (isCode(fallback) ? fallback : undefined);
  const mapped = code ? byPattern(code) : null;
  // Known codes win; then a human message the BFF wrote; then a readable error string.
  if (mapped && (fromError.code || fromDetail.code)) return mapped;
  if (message) return message;
  if (fromError.text && !/\[object Object\]/.test(fromError.text)) return fromError.text;
  if (mapped) return mapped;
  return isCode(fallback) ? GENERIC : fallback || GENERIC;
}

/** For values already thrown as Error(...) somewhere else: never show a raw code. */
export function humanizeMessage(message: string | null | undefined): string {
  const m = (message || "").trim();
  if (!m || m === "[object Object]") return GENERIC;
  return isCode(m) ? byPattern(m) || GENERIC : m;
}
