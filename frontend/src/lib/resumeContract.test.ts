import { describe, expect, it } from "vitest";
import { fromBackendResume, toBackendResume } from "./resumeContract";

describe("resume contract mapping", () => {
  it("sends the backend field names the API validates", () => {
    const body = toBackendResume({
      work_experiences: [
        { company_name: "Uzinfocom", role_title: "Backend intern", employment_type: "PROJECT", location: "Toshkent", start_date: "2025-09-01", is_current: true, description: "API", technologies: ["Python"] },
      ],
      languages: [{ language: "Ingliz tili", proficiency: "C1", certificate_name: "IELTS", score: "7.5" }],
      achievements: [{ title: "ICPC", category: "OLYMPIAD", issuer: "TATU", awarded_date: "2025-05-01" }],
      career_preferences: { github_username: "student", work_mode: "HYBRID", expected_stipend_uzs: 3000000 },
    }) as Record<string, Array<Record<string, unknown>> | Record<string, unknown>>;

    expect((body.work_experiences as Array<Record<string, unknown>>)[0]).toMatchObject({
      position: "Backend intern",
      work_type: "PROJECT",
      responsibilities: "API",
      location: "Toshkent",
    });
    expect((body.languages as Array<Record<string, unknown>>)[0]).toEqual({
      id: undefined,
      language_name: "Ingliz tili",
      level: "C1",
      certificate_score: "IELTS 7.5",
    });
    expect((body.achievements as Array<Record<string, unknown>>)[0]).toMatchObject({ date: "2025-05-01", category: "OLYMPIAD" });
    expect(body.career_preferences).toMatchObject({
      github_url: "https://github.com/student",
      preferred_work_mode: "HYBRID",
      desired_salary_uzs: 3000000,
    });
  });

  it("reads backend data back into the form shape without losing values", () => {
    const ui = fromBackendResume({
      work_experiences: [{ company_name: "A", position: "Dev", work_type: "FREELANCE", is_current: false, end_date: "2026-01-01", responsibilities: "x", technologies: ["Go"] }],
      languages: [{ language_name: "O'zbek tili", level: "NATIVE", certificate_score: null }, { language_name: "Ingliz", level: "B2", certificate_score: "IELTS 6.5" }],
      education_details: { university_name: "TATU", study_year: "3", graduation_year: "2027" },
      career_preferences: { github_url: "https://github.com/ali", preferred_work_mode: "REMOTE", desired_roles: ["Dev"] },
    });
    expect(ui.work_experiences[0]).toMatchObject({ role_title: "Dev", employment_type: "FREELANCE", description: "x", technologies: ["Go"] });
    expect(ui.languages[0]).toMatchObject({ language: "O'zbek tili", proficiency: "NATIVE", certificate_name: null });
    expect(ui.languages[1]).toMatchObject({ certificate_name: "IELTS", score: "6.5" });
    expect(ui.education_details).toMatchObject({ university_name: "TATU", study_year: 3, graduation_year: 2027 });
    expect(ui.career_preferences).toMatchObject({ github_username: "ali", work_mode: "REMOTE", desired_roles: ["Dev"] });
  });
});
