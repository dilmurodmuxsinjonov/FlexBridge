/**
 * Shared role classification and portal boundary helpers aligned with
 * backend/app/services/auth.py (`roles_for`) and flexbridge.role_catalog.
 *
 * Every authenticated FlexBridge user receives `CANDIDATE` by default plus any
 * elevated ORG, INSTITUTION, or PLATFORM grants, so Student-only isolation
 * strictly checks `CANDIDATE` WITHOUT elevated non-student grants.
 */

export type PortalScope = "CANDIDATE" | "EMPLOYER" | "ACADEMIC" | "OPERATOR";

export const EMPLOYER_ROLE_CODES = [
  "OWNER",
  "HR",
  "HOST_COORDINATOR",
  "MENTOR",
  "BILLING",
  "EMPLOYER",
  "ORGANIZATION",
  "HOST",
] as const;

export const ACADEMIC_ROLE_CODES = [
  "COORDINATOR",
  "TEACHER",
  "ACADEMIC",
  "UNIVERSITY",
] as const;

export const OPERATOR_ROLE_CODES = [
  "OPERATOR",
  "ADMIN",
  "AUDITOR",
  "COMPLIANCE",
  "FINANCE",
  "MODERATOR",
  "OPERATIONS",
  "SECURITY_LEAD",
  "SUPPORT",
] as const;

export const SUPER_ADMIN_ROLE = "ADMIN" as const;

export const ORG_MANAGEMENT_ROLE_CODES = [
  "OWNER",
  "HR",
  "HOST_COORDINATOR",
  "BILLING",
] as const;

export const ORG_MANAGEMENT_ROLE_SET = new Set<string>(ORG_MANAGEMENT_ROLE_CODES);

export function hasOrgManagementRole(roles?: string[] | null): boolean {
  return normalizeRoles(roles).some((role) => ORG_MANAGEMENT_ROLE_SET.has(role));
}

export const EMPLOYER_ROLE_SET = new Set<string>(EMPLOYER_ROLE_CODES);
export const ACADEMIC_ROLE_SET = new Set<string>(ACADEMIC_ROLE_CODES);
export const OPERATOR_ROLE_SET = new Set<string>(OPERATOR_ROLE_CODES);

export const NON_STUDENT_ROLE_SET = new Set<string>([
  ...EMPLOYER_ROLE_CODES,
  ...ACADEMIC_ROLE_CODES,
  ...OPERATOR_ROLE_CODES,
]);

export const PORTAL_ROLE_MAP: Record<PortalScope, readonly string[]> = {
  CANDIDATE: ["CANDIDATE"],
  EMPLOYER: EMPLOYER_ROLE_CODES,
  ACADEMIC: ACADEMIC_ROLE_CODES,
  OPERATOR: OPERATOR_ROLE_CODES,
};

export function normalizeRoles(roles?: string[] | null): string[] {
  if (!Array.isArray(roles)) return [];
  return roles.map((role) => role.trim().toUpperCase()).filter(Boolean);
}

/**
 * Returns true only when the account holds CANDIDATE without any elevated
 * employer, university, or platform operator grants.
 */
export function isStudentOnlyRoles(roles?: string[] | null): boolean {
  const upper = normalizeRoles(roles);
  if (!upper.length) return false;
  return upper.includes("CANDIDATE") && !upper.some((role) => NON_STUDENT_ROLE_SET.has(role));
}

export function isEmployerRoles(roles?: string[] | null): boolean {
  return normalizeRoles(roles).some((role) => EMPLOYER_ROLE_SET.has(role));
}

export function isEmployerOnlyRoles(roles?: string[] | null): boolean {
  const upper = normalizeRoles(roles);
  return (
    upper.some((role) => EMPLOYER_ROLE_SET.has(role)) &&
    !upper.some((role) => ACADEMIC_ROLE_SET.has(role) || OPERATOR_ROLE_SET.has(role))
  );
}

export function isAcademicRoles(roles?: string[] | null): boolean {
  return normalizeRoles(roles).some((role) => ACADEMIC_ROLE_SET.has(role));
}

export function isAcademicOnlyRoles(roles?: string[] | null): boolean {
  const upper = normalizeRoles(roles);
  return (
    upper.some((role) => ACADEMIC_ROLE_SET.has(role)) &&
    !upper.some((role) => EMPLOYER_ROLE_SET.has(role) || OPERATOR_ROLE_SET.has(role))
  );
}

export function isOperatorRoles(roles?: string[] | null): boolean {
  return normalizeRoles(roles).some((role) => OPERATOR_ROLE_SET.has(role));
}

export function isOperatorOnlyRoles(roles?: string[] | null): boolean {
  const upper = normalizeRoles(roles);
  return (
    upper.some((role) => OPERATOR_ROLE_SET.has(role)) &&
    !upper.some((role) => EMPLOYER_ROLE_SET.has(role) || ACADEMIC_ROLE_SET.has(role))
  );
}

/** Returns true when the account holds the platform Super Admin (`ADMIN`) grant. */
export function isSuperAdmin(roles?: string[] | null): boolean {
  return normalizeRoles(roles).includes(SUPER_ADMIN_ROLE);
}

export function isRoleAllowedForPortal(roles: string[], portal?: string): boolean {
  if (!portal) return true;
  const normalized = portal.trim().toUpperCase() as PortalScope;
  if (normalized === "CANDIDATE") {
    return isStudentOnlyRoles(roles);
  }
  const allowed = PORTAL_ROLE_MAP[normalized];
  if (!allowed) return true;
  const upper = normalizeRoles(roles);
  return upper.some((role) => allowed.includes(role));
}

export function resolvePortalDashboard(roles?: string[] | null): {
  portal: PortalScope;
  href: string;
  label: string;
  badgeClass: string;
} {
  const upper = normalizeRoles(roles);
  if (upper.some((r) => (OPERATOR_ROLE_CODES as readonly string[]).includes(r))) {
    return {
      portal: "OPERATOR",
      href: "/operator",
      label: "Operator Markazi",
      badgeClass: "border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20",
    };
  }
  if (upper.some((r) => (EMPLOYER_ROLE_CODES as readonly string[]).includes(r))) {
    return {
      portal: "EMPLOYER",
      href: "/employer",
      label: "Korxona Kabineti",
      badgeClass: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20",
    };
  }
  if (upper.some((r) => (ACADEMIC_ROLE_CODES as readonly string[]).includes(r))) {
    return {
      portal: "ACADEMIC",
      href: "/university",
      label: "OTM Portali",
      badgeClass: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20",
    };
  }
  return {
    portal: "CANDIDATE",
    href: "/nomzod",
    label: "Talaba Kabineti",
    badgeClass: "border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20",
  };
}

/**
 * Operator console modules each platform role may open. Mirrors the backend
 * guards (platform_admin, operator_security, feature_flag_admin, operations,
 * owner_continuity, moderation_appeals, privacy, operator_finance, support_tickets)
 * so the UI neither fetches nor shows modules that would only answer 403.
 * The backend remains the authority.
 */
export type OperatorModule =
  | "OVERVIEW"
  | "STAFF_ROLES"
  | "DIRECTORY"
  | "FEATURE_FLAGS"
  | "PRIVACY_REQUESTS"
  | "RECOVERY_REVIEWS"
  | "APPEALS"
  | "CONTINUITY"
  | "OPERATIONS"
  | "AUDIT"
  | "VERIFICATION"
  | "MODERATION"
  | "BREAK_GLASS"
  | "SUPPORT_TICKETS"
  | "PLATFORM_HEALTH"
  | "FINANCE";

export const OPERATOR_MODULE_ROLES: Record<OperatorModule, readonly string[]> = {
  OVERVIEW: OPERATOR_ROLE_CODES,
  STAFF_ROLES: ["ADMIN", "SECURITY_LEAD"],
  DIRECTORY: ["ADMIN", "SECURITY_LEAD", "OPERATIONS", "AUDITOR", "MODERATOR"],
  FEATURE_FLAGS: ["ADMIN", "AUDITOR", "OPERATIONS"],
  PRIVACY_REQUESTS: ["ADMIN", "COMPLIANCE", "SUPPORT", "MODERATOR"],
  RECOVERY_REVIEWS: ["ADMIN", "SUPPORT"],
  APPEALS: ["MODERATOR"],
  CONTINUITY: ["MODERATOR", "COMPLIANCE"],
  OPERATIONS: ["ADMIN", "COMPLIANCE"],
  AUDIT: ["ADMIN", "AUDITOR"],
  VERIFICATION: ["MODERATOR"],
  // Vacancy moderation (GET /moderation/opportunities, POST /moderation/actions) is MODERATOR-only.
  MODERATION: ["MODERATOR"],
  BREAK_GLASS: ["ADMIN", "SECURITY_LEAD", "OPERATIONS"],
  SUPPORT_TICKETS: ["SUPPORT", "ADMIN", "MODERATOR"],
  PLATFORM_HEALTH: ["ADMIN", "OPERATIONS", "SECURITY_LEAD", "AUDITOR"],
  FINANCE: ["FINANCE", "ADMIN"],
};

export function canUseOperatorModule(roles: string[] | null | undefined, module: OperatorModule): boolean {
  const upper = normalizeRoles(roles);
  return upper.some((role) => OPERATOR_MODULE_ROLES[module].includes(role));
}

export interface RoleAuthoritySummaryItem {
  code: string;
  scope: "BASE" | "ORG" | "INSTITUTION" | "PLATFORM";
  labelUz: string;
  grantedByUz: string;
  purposeUz: string;
  requiresMfa: boolean;
  guardrailUz: string;
}

/** Authoritative Uzbek summary of who grants each role and what guardrails apply. */
export const ROLE_AUTHORITY_SUMMARY: readonly RoleAuthoritySummaryItem[] = [
  {
    code: "ADMIN",
    scope: "PLATFORM",
    labelUz: "Bosh administrator (Super Admin)",
    grantedByUz: "Dastlab CLI (Tizim Vakolati), so‘ng amaldagi MFA-tasdiqlangan Bosh administrator",
    purposeUz: "Xodimlarga rol berish/bekor qilish, R1 funksional flaglar, audit, moliya va favqulodda nazorat",
    requiresMfa: true,
    guardrailUz: "O‘ziga rol berish, o‘z ADMIN huquqini bekor qilish va oxirgi faol ADMINni olib tashlash taqiqlanadi",
  },
  {
    code: "SECURITY_LEAD",
    scope: "PLATFORM",
    labelUz: "Xavfsizlik rahbari",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Xodimlar huquqlari reyestrini ko‘rish, foydalanuvchi katalogi, tizim holati va favqulodda ruxsatlar",
    requiresMfa: true,
    guardrailUz: "Doimiy rol bera olmaydi; favqulodda ruxsat ikkinchi tasdiqlovchi bilan ishlaydi",
  },
  {
    code: "OPERATIONS",
    scope: "PLATFORM",
    labelUz: "Operatsiyalar muhandisi",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Tizim barqarorligi, kataloglar, R1 flaglar ko‘rinishi, tiklash mashqlari va hodisalar boshqaruvi",
    requiresMfa: true,
    guardrailUz: "Global flaglarni yoqish/o‘chirish faqat ADMIN huquqiga tegishli",
  },
  {
    code: "COMPLIANCE",
    scope: "PLATFORM",
    labelUz: "Muvofiqlik (Komplayens) nazoratchisi",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Korxona egasi vorisligining 2-bosqich qarori, GDPR maxfiylik so‘rovlari va saqlash muddati (retention) bahosi",
    requiresMfa: true,
    guardrailUz: "Vorislik qarori moderatordan mustaqil boshqa shaxs tomonidan qabul qilinadi",
  },
  {
    code: "MODERATOR",
    scope: "PLATFORM",
    labelUz: "Moderator",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Korxona va OTM tekshiruvi (KYB), e’lonlar moderatsiyasi, apellyatsiyalar va vorislikning 1-bosqichi",
    requiresMfa: true,
    guardrailUz: "O‘zi yozgan e’lon yoki avval o‘zi rad etgan ish bo‘yicha apellyatsiyani ko‘ra olmaydi",
  },
  {
    code: "AUDITOR",
    scope: "PLATFORM",
    labelUz: "Tizim auditori",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "O‘zgarmas audit jurnali, kataloglar, funksional flaglar va tizim holatini faqat o‘qish rejimida nazorat qilish",
    requiresMfa: true,
    guardrailUz: "Faqat o‘qish va tekshirish; hisob yoki to‘lovlarni o‘zgartira olmaydi",
  },
  {
    code: "FINANCE",
    scope: "PLATFORM",
    labelUz: "Moliya nazoratchisi",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Tushum hisoboti, to‘lov shlyuzlari bilan solishtiruv va mablag‘ qaytarishni ikki bosqichli tasdiqlash",
    requiresMfa: true,
    guardrailUz: "Qaytarish so‘rovida birinchi va ikkinchi tasdiqlovchi har xil bo‘lishi shart",
  },
  {
    code: "SUPPORT",
    scope: "PLATFORM",
    labelUz: "Yordam xizmati operatori",
    grantedByUz: "Faqat MFA-tasdiqlangan Bosh administrator (ADMIN)",
    purposeUz: "Murojaatlar navbati, maxfiylik so‘rovlari va hisobga kirishni tiklash arizalarini ko‘rib chiqish",
    requiresMfa: true,
    guardrailUz: "O‘z hisobi bo‘yicha tiklash so‘rovini tasdiqlash tizim tomonidan bloklanadi",
  },
  {
    code: "OWNER",
    scope: "ORG",
    labelUz: "Korxona asosiy egasi",
    grantedByUz: "Korxona asoschisi (KYB tasdig‘idan so‘ng) yoki 2 bosqichli vorislik qarori (MODERATOR → COMPLIANCE)",
    purposeUz: "Korxona jamoasiga rol berish/olish, tariflar, shartnomalar va asosiy boshqaruv",
    requiresMfa: true,
    guardrailUz: "Oxirgi faol korxona egasi o‘zini-o‘zi olib tashlay olmaydi",
  },
  {
    code: "HR",
    scope: "ORG",
    labelUz: "Korxona HR menejeri",
    grantedByUz: "Korxona asosiy egasi (OWNER)",
    purposeUz: "E’lonlar yaratish, nomzodlar arizalari va intervyularni boshqarish",
    requiresMfa: false,
    guardrailUz: "Faqat o‘z tashkiloti doirasida ishlaydi",
  },
  {
    code: "HOST_COORDINATOR",
    scope: "ORG",
    labelUz: "Amaliyot koordinatori (Korxona)",
    grantedByUz: "Korxona asosiy egasi (OWNER)",
    purposeUz: "OTM bilan amaliyot kelishuvlari, kvotalar va joylashtirish jarayonlari",
    requiresMfa: false,
    guardrailUz: "Faqat o‘z tashkiloti doirasida ishlaydi",
  },
  {
    code: "MENTOR",
    scope: "ORG",
    labelUz: "Amaliyot mentori",
    grantedByUz: "Korxona asosiy egasi (OWNER)",
    purposeUz: "Biriktirilgan talabalar amaliyot kundaligi va davomatini tasdiqlash",
    requiresMfa: false,
    guardrailUz: "Faqat o‘ziga biriktirilgan talabalar kundaligini baholaydi",
  },
  {
    code: "BILLING",
    scope: "ORG",
    labelUz: "Korxona moliya mas’uli",
    grantedByUz: "Korxona asosiy egasi (OWNER)",
    purposeUz: "Tarif sotib olish, hisob-fakturalar va to‘lov hujjatlari",
    requiresMfa: false,
    guardrailUz: "Faqat o‘z tashkilotining to‘lov bo‘limiga ruxsat beriladi",
  },
  {
    code: "COORDINATOR",
    scope: "INSTITUTION",
    labelUz: "OTM koordinatori (Dekanat)",
    grantedByUz: "OTM tekshiruvi tasdiqlanganda tizim orqali yoki mavjud MFA-tasdiqlangan OTM koordinatori",
    purposeUz: "Talabalikni tasdiqlash, guruhlar, jadvallar, amaliyot shartnomalari va talaba parolini tiklash",
    requiresMfa: true,
    guardrailUz: "Faqat o‘z universiteti talabalariga nisbatan amal qiladi",
  },
  {
    code: "TEACHER",
    scope: "INSTITUTION",
    labelUz: "OTM o‘qituvchisi / rahbari",
    grantedByUz: "OTM koordinatori (COORDINATOR)",
    purposeUz: "Biriktirilgan talabalar kundaligi, hisobotlar va amaliyot yakuniy bahosi",
    requiresMfa: false,
    guardrailUz: "Faqat biriktirilgan akademik guruhlar bilan ishlaydi",
  },
  {
    code: "CANDIDATE",
    scope: "BASE",
    labelUz: "Talaba / Nomzod (bazaviy)",
    grantedByUz: "Ro‘yxatdan o‘tishda barcha foydalanuvchilarga avtomatik beriladi",
    purposeUz: "Profil, rezyume, dars jadvali, vakansiyalarga ariza va amaliyot kundaligi",
    requiresMfa: false,
    guardrailUz: "Yuqori lavozim berilganda boshqa portallar uchun alohida izolyatsiya qilinadi",
  },
];
