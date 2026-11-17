import { describe, expect, it } from "vitest";
import {
  ROLE_AUTHORITY_SUMMARY,
  canUseOperatorModule,
  isAcademicOnlyRoles,
  isEmployerOnlyRoles,
  isOperatorOnlyRoles,
  isRoleAllowedForPortal,
  isStudentOnlyRoles,
  isSuperAdmin,
  normalizeRoles,
  resolvePortalDashboard,
} from "./roles";

describe("normalizeRoles", () => {
  it("upper-cases, trims and drops empty values", () => {
    expect(normalizeRoles([" candidate ", "hr", ""])).toEqual(["CANDIDATE", "HR"]);
  });

  it("returns an empty list for missing input", () => {
    expect(normalizeRoles(null)).toEqual([]);
    expect(normalizeRoles(undefined)).toEqual([]);
  });
});

describe("isStudentOnlyRoles", () => {
  it("accepts a plain candidate", () => {
    expect(isStudentOnlyRoles(["CANDIDATE"])).toBe(true);
  });

  it("rejects candidates that also hold an elevated grant", () => {
    expect(isStudentOnlyRoles(["CANDIDATE", "HR"])).toBe(false);
    expect(isStudentOnlyRoles(["CANDIDATE", "TEACHER"])).toBe(false);
    expect(isStudentOnlyRoles(["CANDIDATE", "AUDITOR"])).toBe(false);
  });

  it("rejects empty role lists", () => {
    expect(isStudentOnlyRoles([])).toBe(false);
  });
});

describe("only-role helpers", () => {
  it("separates employer, academic and operator grants", () => {
    expect(isEmployerOnlyRoles(["CANDIDATE", "OWNER"])).toBe(true);
    expect(isEmployerOnlyRoles(["OWNER", "COORDINATOR"])).toBe(false);
    expect(isAcademicOnlyRoles(["CANDIDATE", "TEACHER"])).toBe(true);
    expect(isAcademicOnlyRoles(["TEACHER", "ADMIN"])).toBe(false);
    expect(isOperatorOnlyRoles(["CANDIDATE", "SECURITY_LEAD"])).toBe(true);
    expect(isOperatorOnlyRoles(["SUPPORT", "BILLING"])).toBe(false);
  });
});

describe("isRoleAllowedForPortal", () => {
  it.each([
    [["CANDIDATE"], "CANDIDATE", true],
    [["CANDIDATE", "HR"], "CANDIDATE", false],
    [["CANDIDATE", "HR"], "EMPLOYER", true],
    [["CANDIDATE"], "EMPLOYER", false],
    [["CANDIDATE", "COORDINATOR"], "ACADEMIC", true],
    [["CANDIDATE", "COORDINATOR"], "OPERATOR", false],
    [["CANDIDATE", "MODERATOR"], "operator", true],
  ])("roles %j on portal %s -> %s", (roles, portal, expected) => {
    expect(isRoleAllowedForPortal(roles, portal)).toBe(expected);
  });

  it("does not restrict when no portal is requested", () => {
    expect(isRoleAllowedForPortal(["CANDIDATE"], undefined)).toBe(true);
  });
});

describe("resolvePortalDashboard", () => {
  it.each([
    [["CANDIDATE"], "/nomzod"],
    [["CANDIDATE", "MENTOR"], "/employer"],
    [["CANDIDATE", "TEACHER"], "/university"],
    [["CANDIDATE", "FINANCE"], "/operator"],
    [["CANDIDATE", "COMPLIANCE"], "/operator"],
    [["CANDIDATE", "OPERATIONS"], "/operator"],
    [null, "/nomzod"],
  ])("routes %j to %s", (roles, href) => {
    expect(resolvePortalDashboard(roles).href).toBe(href);
  });

  it("uses Operator Markazi label instead of SOC Terminal", () => {
    const resolved = resolvePortalDashboard(["ADMIN"]);
    expect(resolved.portal).toBe("OPERATOR");
    expect(resolved.label).toBe("Operator Markazi");
  });

  it("prefers the operator workspace over employer and academic grants", () => {
    expect(resolvePortalDashboard(["OWNER", "TEACHER", "ADMIN"]).portal).toBe("OPERATOR");
  });
});

describe("isSuperAdmin", () => {
  it("recognizes ADMIN regardless of casing", () => {
    expect(isSuperAdmin(["candidate", "admin"])).toBe(true);
    expect(isSuperAdmin(["SECURITY_LEAD", "MODERATOR"])).toBe(false);
    expect(isSuperAdmin(null)).toBe(false);
  });
});

describe("canUseOperatorModule", () => {
  it("lets a moderator open verification, moderation, appeals, continuity, directory, privacy and support only", () => {
    const roles = ["CANDIDATE", "MODERATOR"];
    expect(canUseOperatorModule(roles, "VERIFICATION")).toBe(true);
    expect(canUseOperatorModule(roles, "MODERATION")).toBe(true);
    expect(canUseOperatorModule(roles, "APPEALS")).toBe(true);
    expect(canUseOperatorModule(roles, "CONTINUITY")).toBe(true);
    expect(canUseOperatorModule(roles, "DIRECTORY")).toBe(true);
    expect(canUseOperatorModule(roles, "PRIVACY_REQUESTS")).toBe(true);
    expect(canUseOperatorModule(roles, "SUPPORT_TICKETS")).toBe(true);
    expect(canUseOperatorModule(roles, "STAFF_ROLES")).toBe(false);
    expect(canUseOperatorModule(roles, "FEATURE_FLAGS")).toBe(false);
    expect(canUseOperatorModule(roles, "RECOVERY_REVIEWS")).toBe(false);
    expect(canUseOperatorModule(roles, "OPERATIONS")).toBe(false);
    expect(canUseOperatorModule(roles, "AUDIT")).toBe(false);
    expect(canUseOperatorModule(roles, "FINANCE")).toBe(false);
    expect(canUseOperatorModule(roles, "PLATFORM_HEALTH")).toBe(false);
  });

  it("maps compliance, security lead, operations, and support modules to backend guards", () => {
    expect(canUseOperatorModule(["COMPLIANCE"], "CONTINUITY")).toBe(true);
    expect(canUseOperatorModule(["COMPLIANCE"], "OPERATIONS")).toBe(true);
    expect(canUseOperatorModule(["COMPLIANCE"], "PRIVACY_REQUESTS")).toBe(true);
    expect(canUseOperatorModule(["COMPLIANCE"], "APPEALS")).toBe(false);

    expect(canUseOperatorModule(["SECURITY_LEAD"], "STAFF_ROLES")).toBe(true);
    expect(canUseOperatorModule(["SECURITY_LEAD"], "DIRECTORY")).toBe(true);
    expect(canUseOperatorModule(["SECURITY_LEAD"], "BREAK_GLASS")).toBe(true);
    expect(canUseOperatorModule(["SECURITY_LEAD"], "FEATURE_FLAGS")).toBe(false);

    expect(canUseOperatorModule(["OPERATIONS"], "FEATURE_FLAGS")).toBe(true);
    expect(canUseOperatorModule(["OPERATIONS"], "PLATFORM_HEALTH")).toBe(true);
    expect(canUseOperatorModule(["OPERATIONS"], "STAFF_ROLES")).toBe(false);

    expect(canUseOperatorModule(["SUPPORT"], "RECOVERY_REVIEWS")).toBe(true);
    expect(canUseOperatorModule(["SUPPORT"], "PRIVACY_REQUESTS")).toBe(true);
    expect(canUseOperatorModule(["SUPPORT"], "DIRECTORY")).toBe(false);
  });

  it("gives finance staff the finance module", () => {
    expect(canUseOperatorModule(["FINANCE"], "FINANCE")).toBe(true);
    expect(canUseOperatorModule(["FINANCE"], "AUDIT")).toBe(false);
  });

  it("gives admins Super Admin modules while keeping moderator-only queues isolated", () => {
    for (const m of [
      "OVERVIEW",
      "STAFF_ROLES",
      "DIRECTORY",
      "FEATURE_FLAGS",
      "PRIVACY_REQUESTS",
      "RECOVERY_REVIEWS",
      "OPERATIONS",
      "AUDIT",
      "BREAK_GLASS",
      "SUPPORT_TICKETS",
      "PLATFORM_HEALTH",
      "FINANCE",
    ] as const) {
      expect(canUseOperatorModule(["admin"], m)).toBe(true);
    }
    expect(canUseOperatorModule(["ADMIN"], "VERIFICATION")).toBe(false);
    expect(canUseOperatorModule(["ADMIN"], "MODERATION")).toBe(false);
    expect(canUseOperatorModule(["ADMIN"], "APPEALS")).toBe(false);
    expect(canUseOperatorModule(["ADMIN"], "CONTINUITY")).toBe(false);
  });
});

describe("ROLE_AUTHORITY_SUMMARY", () => {
  it("documents platform, org, institution, and base roles in Uzbek", () => {
    const codes = new Set(ROLE_AUTHORITY_SUMMARY.map((item) => item.code));
    for (const required of [
      "ADMIN",
      "SECURITY_LEAD",
      "OPERATIONS",
      "COMPLIANCE",
      "MODERATOR",
      "AUDITOR",
      "FINANCE",
      "SUPPORT",
      "OWNER",
      "COORDINATOR",
      "CANDIDATE",
    ]) {
      expect(codes.has(required)).toBe(true);
    }
  });
});
