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
  TIMETABLE_SLOT_OVERLAP: "Bu guruhda shu kuni va shu vaqtda boshqa dars bor. Boshqa para yoki vaqtni tanlang.",
  INVALID_TIMETABLE_TIME_RANGE: "Dars vaqti noto‘g‘ri: tugash boshlanishdan keyin va 06:00–23:00 oralig‘ida bo‘lsin.",
  INVALID_TIMETABLE_GROUP_CODE: "Guruh kodini kiriting (2–60 belgi).",
  INVALID_TIMETABLE_SUBJECT_NAME: "Fan nomini kiriting (2–200 belgi).",
  TIMETABLE_SLOTS_LIMIT_EXCEEDED: "Jadvalda 500 tadan ortiq dars bo‘lishi mumkin emas.",
  APPLICATION_ALREADY_EXISTS: "Siz bu e’longa allaqachon ariza topshirgansiz — holatini «Arizalarim» bo‘limida kuzating.",
  ALREADY_APPLIED: "Siz bu e’longa allaqachon ariza topshirgansiz — holatini «Arizalarim» bo‘limida kuzating.",
  MODERATION_APPROVAL_REQUIRED: "E’lon hali moderatordan o‘tmagan. Tasdiqlangach e’lon qilishingiz mumkin.",
  ACTIVE_ENTITLEMENT_REQUIRED: "E’lon qilish uchun faol tarif kerak — «To‘lovlar va tariflar» bo‘limidan tanlang.",
  SELF_ROLE_GRANT_FORBIDDEN: "O‘zingizga platforma rolini bera olmaysiz.",
  LAST_ADMIN_CANNOT_BE_REVOKED: "Tizimdagi oxirgi faol Bosh administrator huquqini bekor qilib bo‘lmaydi.",
  SELF_ADMIN_REVOKE_FORBIDDEN: "O‘z administrator huquqingizni o‘zingiz bekor qila olmaysiz.",
  GRANT_ALREADY_ACTIVE: "Bu foydalanuvchida ushbu rol allaqachon faol.",
  GRANT_ALREADY_REVOKED: "Bu rol ruxsati allaqachon bekor qilingan.",
  TARGET_USER_NOT_ACTIVE: "Tanlangan foydalanuvchi hisobi faol holatda emas.",
  ROLE_SCOPE_MISMATCH: "Tanlangan rol platforma doirasiga mos kelmaydi.",
  ACCOUNT_RECOVERY_ALREADY_DECIDED: "Hisobni tiklash so‘rovi allaqachon ko‘rib chiqilgan.",
  ACCOUNT_RECOVERY_NOT_AVAILABLE: "Hisobni tiklash so‘rovi topilmadi yoki muddati tugagan.",
  ACCOUNT_RECOVERY_SELF_REVIEW_FORBIDDEN: "O‘zingizning hisob tiklash so‘rovingizni ko‘rib chiqa olmaysiz.",
  RECOVERY_REQUEST_NOT_AVAILABLE: "Hisobni tiklash so‘rovi topilmadi yoki allaqachon hal qilingan.",
  RECOVERY_DECISION_REASON_REQUIRED: "Qaror sababi kamida 15 belgidan iborat bo‘lishi kerak.",
  SELF_REVIEW_FORBIDDEN: "O‘z so‘rovingiz bo‘yicha qaror qabul qila olmaysiz.",
  FEATURE_PREREQUISITES_UNMET: "Bu himoyalangan funksiyani R1 bosqichida yoqish uchun talablar bajarilmagan.",
  R2_FEATURE_OUT_OF_R1_SCOPE: "Keyingi bosqich (R2) funksiyasini joriy R1 muhitida yoqib bo‘lmaydi.",
  FEATURE_FLAG_ALIAS_READ_ONLY: "Bu flag taxallusi faqat ko‘rish uchun — asosiy flagni boshqaring.",
  STALE_FEATURE_FLAG_VERSION: "Flag holati boshqa administrator tomonidan o‘zgartirilgan. Ro‘yxatni yangilab qayta urining.",
  INVALID_FEATURE_FLAG_REASON: "O‘zgartirish sababi kamida 15 belgidan iborat bo‘lishi kerak.",
  FEATURE_FLAG_AUTHORITY_REQUIRED: "Flagni o‘zgartirish uchun faol ADMIN va 2FA (MFA) sessiyasi talab etiladi.",
  IDEMPOTENCY_KEY_REUSED: "Bir xil so‘rov kaliti boshqa parametrlar bilan qayta yuborildi.",
  IF_MATCH_REQUIRED: "Versiya tekshiruvi sarlavhasi yetishmayapti. Ro‘yxatni yangilang.",
  INVALID_IF_MATCH: "Flag versiyasi mos kelmadi. Ro‘yxatni yangilang.",
  APPEAL_ALREADY_ASSIGNED: "Bu apellyatsiya allaqachon boshqa moderatorga biriktirilgan.",
  APPEAL_NOT_ASSIGNED: "Qaror chiqarishdan oldin apellyatsiyani o‘zingizga biriktiring.",
  APPEAL_DECISION_STALE: "E’lon holati o‘zgarganligi sababli apellyatsiya qarori eskirgan.",
  APPEAL_REVIEWER_CONFLICT: "Asl moderatsiyani o‘tkazgan yoki korxonaga aloqador shaxs bu apellyatsiyani ko‘ra olmaydi.",
  CASE_ASSIGNED_TO_OTHER: "Bu ariza allaqachon boshqa xodim tomonidan olingan.",
  ASSIGNED_REVIEW_REQUIRED: "Qaror chiqarishdan oldin arizani o‘zingizga biriktiring.",
  CONTINUITY_DISTINCT_REVIEWERS_REQUIRED: "Moderator va Komplayens bosqichlarini ikki xil mustaqil xodim ko‘rib chiqishi shart.",
  CONTINUITY_STAGE_CONFLICT: "Ariza boshqa ko‘rib chiqish bosqichiga o‘tib ketgan.",
  CONTINUITY_CLAIM_NO_LONGER_CURRENT: "Biriktiruv muddati yoki vakolati yangilangan. Ro‘yxatni yangilang.",
  FORBIDDEN_ROLE: "Bu amal uchun joriy rolingizda ruxsat yetarli emas.",
  PERMISSION_DENIED: "Bu amal uchun ruxsatingiz yo‘q.",
  EXACTLY_ONE_TARGET_REQUIRED: "Shikoyat qilinayotgan ob’ekt aniq ko‘rsatilishi shart.",
  MODERATION_REPORT_FAILED: "Murojaatni moderatsiyaga yuborib bo‘lmadi.",
  ORGANIZATION_NOT_FOUND: "Tasdiqlangan tashkilot profili topilmadi.",
  OPPORTUNITY_NOT_DRAFT: "Faqat qoralama (DRAFT) holatidagi e’lonni tahrirlash mumkin.",
  HOST_COORDINATOR_INTERNSHIP_ONLY: "Amaliyot koordinatori faqat amaliyot e’lonlarini tahrirlay oladi.",
  CAPACITY_LESS_THAN_OCCUPIED: "Kvota allaqachon qabul qilingan o‘rinlar sonidan kam bo‘lmasligi kerak.",
  UNPAID_PART_TIME_FORBIDDEN: "Yarim stavkali ish e’lonlari albatta haq to‘lanadigan bo‘lishi shart.",
  OVERLAPPING_OPPORTUNITY_SHIFT: "Bir xil guruh va hafta kunida ish smenalari ustma-ust tushmasligi kerak.",
  OWNER_CONTACT_NOT_VERIFIED: "Rozilik uchun tasdiqlangan telefon yoki elektron pochta tanlanishi shart.",
  OWNER_TARGET_CONSENT_REQUIRED: "Avval nomzod xodimning shaxsiy roziligi olinishi kerak.",
  CONTINUITY_APPLICANT_ALREADY_OWNER: "Siz allaqachon ushbu tashkilot rahbari (OWNER) hisoblanasiz.",
  CONTINUITY_REQUEST_ALREADY_PENDING: "Ushbu tashkilot uchun ochiq vorislik arizasi allaqachon ko‘rib chiqilmoqda.",
  CONTINUITY_ACTIVE_OWNER_ROSTER_REQUIRED: "Vorislik so‘rovi uchun tashkilotda faol OWNER ro‘yxati mavjud bo‘lishi shart.",
  OPEN_LOGS_NEED_REVISION: "Amaliyotni yakunlashdan oldin «Tuzatish kerak» holatidagi kundaliklarni qayta yuboring.",
  PERSONAL_MENTOR_ACCEPTANCE_REQUIRED: "Boshlashdan oldin biriktirilgan mentor tayinlovni shaxsan qabul qilishi kerak.",
  CANDIDATE_PLAN_ACCEPTANCE_REQUIRED: "Faollashtirishdan oldin talaba amaliyot rejasini qabul qilishi shart.",
  ACTIVE_PLAN_AMENDMENT_REQUIRED: "Faol amaliyot rejasi endi to‘g‘ridan-to‘g‘ri o‘zgartirilmaydi.",
  SUBMITTED_LOG_IMMUTABLE: "Tekshiruvga yuborilgan kundalik vazifasiga endi yangi dalil biriktirib bo‘lmaydi.",
  EVIDENCE_ALREADY_ATTACHED: "Ushbu fayl dalil sifatida allaqachon biriktirilgan.",
  FILE_NOT_CLEAN_FOR_EVIDENCE: "Fayl antivirus tekshiruvidan toza (CLEAN) o‘tmagan.",
  INSUFFICIENT_LOGGED_MINUTES: "Minimal talab qilingan soatlar bajarilmagan — muddatidan oldin yakunlash sababini kiriting.",
  PLACEMENT_NOT_ACTIVE: "Bu amal faqat faol amaliyot (ACTIVE) holatida bajariladi.",
  PLACEMENT_ALREADY_COMPLETED: "Amaliyot allaqachon yakunlangan.",
  PASSKEY_CONFIGURATION_REQUIRED: "Serverda Passkey (WebAuthn) RP sozlamalari yoqilmagan.",
  PASSKEY_VERIFICATION_FAILED: "Passkey tasdig‘i muvaffaqiyatsiz tugadi. Qayta urinib ko‘ring.",
  PASSKEY_SCOPE_FORBIDDEN: "Ushbu Passkey boshqa hisobga tegishli.",
  PASSKEY_NOT_FOUND: "Passkey topilmadi yoki allaqachon bekor qilingan.",
  PASSKEY_CREDENTIAL_REQUIRED: "Brauzerdan Passkey tasdig‘i olinmadi.",
  WEBAUTHN_UNSUPPORTED: "Joriy brauzer yoki qurilma Passkey (WebAuthn) ni qo‘llab-quvvatlamaydi.",
  WEBAUTHN_CANCELLED: "Passkey tasdig‘i bekor qilindi.",
  CONTACT_SCOPE_FORBIDDEN: "Faqat o‘zingizning hisobingizga aloqa manzilini bog‘lashingiz mumkin.",
  CONTACT_BIND_FAILED: "Aloqa manzilini bog‘lashda xatolik yuz berdi.",
  CHALLENGE_RESEND_FAILED: "Kod qayta yuborilmadi. Taymer tugashini kuting.",
  ENROLLMENT_RESUBMISSION_STATE_CONFLICT: "Ushbu talabalik holatida hujjatni qayta topshirish mumkin emas.",
  ENROLLMENT_EVIDENCE_REQUIRED: "Kamida bitta tasdiqlovchi PDF hujjat yuklash talab qilinadi.",
  ENROLLMENT_EVIDENCE_NOTE_INVALID: "Izoh kamida 15 ta belgidan iborat bo‘lishi kerak.",
  APPEAL_ALREADY_SUBMITTED: "Ushbu rad qarori bo‘yicha apellyatsiya allaqachon yuborilgan.",
  APPEAL_REASON_REQUIRED: "Apellyatsiya sababi kamida 15 ta belgidan iborat bo‘lishi kerak.",
  CURRENT_VERIFIED_ENROLLMENT_REQUIRED: "Faqat joriy va OTM tasdiqlagan talabalik yozuvini ulash mumkin.",
  PENDING_ACADEMIC_PLACEMENT_REQUIRED: "Faqat rejalashtirilgan dual ta’lim amaliyoti uchun akademik kuzatuv so‘raladi.",
  SCHOOL_BINDING_AMENDMENT_REQUIRED: "Bu amaliyotga OTM kuzatuvi allaqachon biriktirilgan.",
  INVALID_DISPLAY_NAME: "Ism-familiya kamida 2 ta belgidan iborat bo‘lishi kerak.",
  PASSWORD_UNCHANGED: "Yangi parol joriy paroldan farq qilishi kerak.",
  LAST_CONTACT_CANNOT_BE_REMOVED: "Hisobda kamida bitta tasdiqlangan telefon yoki e-pochta qolishi shart.",
  CONTACT_NOT_FOUND: "Aloqa manzili topilmadi yoki allaqachon o‘chirilgan.",
  PROFILE_UPDATE_FAILED: "Foydalanuvchi nomini yangilab bo‘lmadi.",
  PASSWORD_CHANGE_FAILED: "Parolni yangilab bo‘lmadi. Joriy parol va tasdiq kodini tekshiring.",
  CONTACT_PRIMARY_UPDATE_FAILED: "Asosiy kirish manzilini o‘zgartirib bo‘lmadi.",
  CONTACT_REMOVE_FAILED: "Aloqa manzilini o‘chirib bo‘lmadi.",
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
  if (/_OVERLAP$/.test(code)) return "Vaqt boshqa yozuv bilan to‘qnashadi. Boshqa vaqtni tanlang.";
  if (/(_ALREADY_EXISTS|_EXISTS|_DUPLICATE)$/.test(code)) return "Bu yozuv allaqachon mavjud.";
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
