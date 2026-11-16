/**
 * Human (Uzbek) labels for backend enum values. Unknown values are softened
 * (UPPER_SNAKE -> "Upper snake") instead of being shown as raw machine codes.
 */

const LABELS: Record<string, string> = {
  // Opportunity kind / contract / work mode
  INTERNSHIP: "Amaliyot",
  PART_TIME: "Yarim stavka",
  FULL_TIME: "To‘liq stavka",
  INTERNSHIP_AGREEMENT: "Amaliyot shartnomasi",
  PAID_INTERNSHIP_CONTRACT: "Haq to‘lanadigan amaliyot",
  LABOR_PART_TIME: "Yarim stavka mehnat shartnomasi",
  LABOR_FULL_TIME: "To‘liq stavka mehnat shartnomasi",
  CIVIL_GPC: "Fuqarolik-huquqiy shartnoma",
  ONSITE: "Ish joyida",
  HYBRID: "Gibrid",
  REMOTE: "Masofadan",
  // Skill levels
  BEGINNER: "Boshlang‘ich",
  INTERMEDIATE: "O‘rta",
  ADVANCED: "Yuqori",
  EXPERT: "Ekspert",
  SELF_DECLARED: "O‘zi ko‘rsatgan",
  VERIFIED: "Tasdiqlangan",
  // Availability
  AVAILABLE: "Bo‘sh",
  UNAVAILABLE: "Band",
  // Organization / institution roles
  OWNER: "Asosiy egasi",
  OPERATOR: "Operator",
  AUDITOR: "Auditor",
  FINANCE: "Moliya",
  MODERATOR: "Moderator",
  SECURITY_LEAD: "Xavfsizlik rahbari",
  SUPPORT: "Yordam xizmati",
  ADMIN: "Administrator",
  RECRUITER: "Rekruter",
  HR_MANAGER: "HR menejer",
  MENTOR: "Mentor",
  MEMBER: "Xodim",
  VIEWER: "Kuzatuvchi",
  FIRST_COORDINATOR: "Bosh koordinator",
  COORDINATOR: "Koordinator",
  STAFF_TEACHER: "O‘qituvchi",
  // Support tickets
  LOW: "Past",
  MEDIUM: "O‘rta",
  NORMAL: "Oddiy",
  HIGH: "Yuqori",
  URGENT: "Shoshilinch",
  CRITICAL: "Juda muhim",
  TECHNICAL: "Texnik",
  BILLING: "To‘lov",
  ACCOUNT: "Hisob",
  SECURITY: "Xavfsizlik",
  PRIVACY: "Maxfiylik",
  CONTENT: "Kontent",
  COMPLAINT: "Shikoyat",
  GENERAL: "Umumiy",
  OTHER: "Boshqa",
  OPEN: "Ochiq",
  NEW: "Yangi",
  IN_PROGRESS: "Ko‘rib chiqilmoqda",
  PENDING_SUPPORT: "Yordam javobi kutilmoqda",
  PENDING_USER: "Sizning javobingiz kutilmoqda",
  PENDING_CUSTOMER: "Mijoz javobi kutilmoqda",
  RESOLVED: "Hal qilindi",
  CLOSED: "Yopildi",
  // Common lifecycle
  DRAFT: "Qoralama",
  PENDING: "Kutilmoqda",
  PENDING_REVIEW: "Ko‘rib chiqilmoqda",
  APPROVED: "Tasdiqlandi",
  REJECTED: "Rad etildi",
  ACTIVE: "Faol",
  INACTIVE: "Faol emas",
  SUSPENDED: "To‘xtatilgan",
  REVOKED: "Bekor qilindi",
  EXPIRED: "Muddati o‘tgan",
  PUBLISHED: "E’lon qilingan",
  ARCHIVED: "Arxivda",
  PAUSED: "To‘xtatilgan",
  SUBMITTED: "Yuborildi",
  WITHDRAWN: "Qaytarib olindi",
  PAID: "To‘langan",
  UNPAID: "To‘lanmagan",
  CANCELLED: "Bekor qilindi",
  COMPLETED: "Yakunlandi",
  // Student enrollment
  DECLARED: "E’lon qilingan",
  IN_REVIEW: "Tekshirilmoqda",
  NEEDS_INFO: "Ma’lumot so‘ralgan",
  ENDED: "Yakunlangan",
  // Billing plans
  BEPUL_KIRISH: "Bepul boshlang‘ich",
  FREE: "Bepul",
  XIZMAT_PAKETI: "Xizmat paketi",
  // Academic agreement / supervision purposes
  ACADEMIC_VIEW: "Akademik nazorat",
  ACADEMIC_NOMINATION: "Ilmiy rahbar tayinlash",
  ACADEMIC_REVOKE: "Rahbarlikni bekor qilish",
  INTERNSHIP_SUPERVISION: "Amaliyot rahbarligi",
  ENROLLMENT_VERIFICATION: "Talabalikni tasdiqlash",
  // University report sources
  MANUAL_ENTRY: "Qo‘lda kiritilgan",
  TEMPLATE_IMPORT: "Shablondan yuklangan",
};

const isCode = (s: string) => /^[A-Z][A-Z0-9_]+$/.test(s);

export function enumLabel(value: string | null | undefined, fallback = "—"): string {
  if (!value) return fallback;
  const v = String(value).trim();
  if (LABELS[v]) return LABELS[v];
  if (!isCode(v)) return v;
  const words = v.toLowerCase().split("_").filter(Boolean).join(" ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function enumLabels(values: readonly string[] | null | undefined): string {
  return (values || []).map((v) => enumLabel(v)).join(", ");
}
