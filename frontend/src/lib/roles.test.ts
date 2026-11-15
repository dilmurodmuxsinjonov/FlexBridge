import { describe, expect, it } from "vitest";
import {
  canUseOperatorModule,
  isAcademicOnlyRoles,
  isEmployerOnlyRoles,
  isOperatorOnlyRoles,
  isRoleAllowedForPortal,
  isStudentOnlyRoles,
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
    [null, "/nomzod"],
  ])("routes %j to %s", (roles, href) => {
    expect(resolvePortalDashboard(roles).href).toBe(href);
  });

  it("prefers the operator workspace over employer and academic grants", () => {
    expect(resolvePortalDashboard(["OWNER", "TEACHER", "ADMIN"]).portal).toBe("OPERATOR");
  });
});

describe("canUseOperatorModule", () => {
  it("lets a moderator open verification and support tickets only", () => {
    const roles = ["CANDIDATE", "MODERATOR"];
    expect(canUseOperatorModule(roles, "VERIFICATION")).toBe(true);
    expect(canUseOperatorModule(roles, "SUPPORT_TICKETS")).toBe(true);
    expect(canUseOperatorModule(roles, "AUDIT")).toBe(false);
    expect(canUseOperatorModule(roles, "FINANCE")).toBe(false);
    expect(canUseOperatorModule(roles, "PLATFORM_HEALTH")).toBe(false);
  });

  it("gives finance staff the finance module", () => {
    expect(canUseOperatorModule(["FINANCE"], "FINANCE")).toBe(true);
    expect(canUseOperatorModule(["FINANCE"], "AUDIT")).toBe(false);
  });

  it("gives admins every module except moderator-only verification", () => {
    for (const m of ["AUDIT", "BREAK_GLASS", "SUPPORT_TICKETS", "PLATFORM_HEALTH", "FINANCE"] as const) {
      expect(canUseOperatorModule(["admin"], m)).toBe(true);
    }
    expect(canUseOperatorModule(["ADMIN"], "VERIFICATION")).toBe(false);
  });
});
