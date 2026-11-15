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
  "FINANCE",
  "MODERATOR",
  "SECURITY_LEAD",
  "SUPPORT",
] as const;

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
      label: "SOC Terminal",
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
