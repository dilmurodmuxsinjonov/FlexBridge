import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchCandidateProfile: vi.fn(),
  fetchCandidateResumeDetails: vi.fn(),
  saveCandidateResumeDetails: vi.fn(),
  updateCandidateProfile: vi.fn(),
  setCandidateVisibility: vi.fn(),
  uploadCandidatePdfFile: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

import ResumeBuilder from "./ResumeBuilder";
import { completeness, experienceMonths, toDraft, validateExperience } from "./resumeDraft";

const resume = {
  ok: true,
  contract_id: "x",
  candidate_id: "c",
  achievements: [],
  work_experiences: [],
  languages: [],
  education_details: { university_name: "", faculty: "", major: "", degree_level: "BAKALAVR", study_year: 3, gpa: "", graduation_year: 2027, thesis_or_research_topic: "" },
  career_preferences: { desired_roles: [], work_mode: "FLEXIBLE", preferred_weekly_hours: 20, expected_stipend_uzs: 0, career_objective: "", linkedin_url: "", telegram_username: "", github_username: "" },
};
const profile = { id: "p", user_id: "u", headline: "", region: "", bio: "", experience_months: 0, visibility: "PRIVATE", skills: [] };

describe("ResumeBuilder", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchCandidateProfile.mockResolvedValue(profile);
    api.fetchCandidateResumeDetails.mockResolvedValue(resume);
    api.saveCandidateResumeDetails.mockResolvedValue(resume);
    api.updateCandidateProfile.mockResolvedValue(profile);
  });

  it("requires a headline before moving on, then saves and advances", async () => {
    render(<ResumeBuilder />);
    const next = await screen.findByRole("button", { name: /Saqlash va davom etish/ });
    fireEvent.click(next);
    expect(await screen.findByText(/Kasbiy sarlavhani yozing/)).toBeInTheDocument();
    expect(api.saveCandidateResumeDetails).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Kasbiy sarlavha"), { target: { value: "Python dasturchi — amaliyot" } });
    fireEvent.change(screen.getByLabelText(/Qanday lavozimlarni/), { target: { value: "Backend amaliyotchi" } });
    fireEvent.keyDown(screen.getByLabelText(/Qanday lavozimlarni/), { key: "Enter" });
    fireEvent.click(next);
    await waitFor(() => expect(api.saveCandidateResumeDetails).toHaveBeenCalled());
    expect(api.saveCandidateResumeDetails.mock.calls[0][0].career_preferences.desired_roles).toEqual(["Backend amaliyotchi"]);
    expect(api.updateCandidateProfile).toHaveBeenCalledWith(expect.objectContaining({ headline: "Python dasturchi — amaliyot" }));
    expect(await screen.findByLabelText("Oliy ta’lim muassasasi")).toBeInTheDocument();
  });

  it("adds an experience through a validated card", async () => {
    api.fetchCandidateProfile.mockResolvedValue({ ...profile, headline: "Dasturchi" });
    render(<ResumeBuilder />);
    fireEvent.click(await screen.findByRole("button", { name: /3\s*Tajriba/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Tajriba qo‘shish/ }));
    fireEvent.click(screen.getByRole("button", { name: /Kartochkani saqlash/ }));
    expect(screen.getByText("Lavozimni yozing (kamida 2 belgi).")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Lavozim"), { target: { value: "Backend amaliyotchi" } });
    fireEvent.change(screen.getByLabelText("Tashkilot"), { target: { value: "Uzinfocom" } });
    fireEvent.change(screen.getByLabelText("Boshlagan oy"), { target: { value: "2025-09" } });
    fireEvent.click(screen.getByLabelText("Hozir ham shu yerda"));
    fireEvent.click(screen.getByRole("button", { name: /Kartochkani saqlash/ }));
    expect(screen.getByText("Backend amaliyotchi · Uzinfocom")).toBeInTheDocument();
  });

  it("explains a load failure with a retry", async () => {
    api.fetchCandidateResumeDetails.mockRejectedValue(new Error("boom"));
    render(<ResumeBuilder />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Rezyumeni yuklab bo‘lmadi");
  });
});

describe("resume draft helpers", () => {
  it("validates experience dates and required fields", () => {
    const e = validateExperience({ company_name: "A", role_title: "", employment_type: "INTERNSHIP", location: "", start_date: "2025-09-01", end_date: "2025-01-01" });
    expect(Object.keys(e).sort()).toEqual(["company_name", "end_date", "role_title"]);
  });

  it("counts overlapping experience months once", () => {
    const today = new Date(2026, 0, 15);
    const months = experienceMonths(
      [
        { company_name: "A", role_title: "x", employment_type: "PROJECT", location: "", start_date: "2025-09-01", end_date: "2025-11-30" },
        { company_name: "B", role_title: "y", employment_type: "PROJECT", location: "", start_date: "2025-11-01", is_current: true },
      ],
      today
    );
    expect(months).toBe(5); // Sep, Oct, Nov, Dec, Jan
  });

  it("reports completeness per section", () => {
    const d = toDraft({ ...profile, headline: "Dasturchi" }, resume);
    expect(completeness(d)).toEqual({ basics: false, education: false, experience: false, languages: false, extras: false });
  });
});
