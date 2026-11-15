import { describe, expect, it } from "vitest";
import {
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
