/**
 * Resume builder draft model (Issue #241). Pure helpers: mapping between the
 * API shapes and the builder, per-step validation and completeness — kept
 * separate from the UI so they are easy to test.
 */
import type {
  CandidateAchievementItem,
  CandidateCareerPreferences,
  CandidateEducationDetails,
  CandidateLanguageItem,
  CandidateProfileData,
  CandidateResumeDetailsResponse,
  CandidateWorkExperienceItem,
} from "@/lib/api";

export type StepId = "basics" | "education" | "experience" | "languages" | "extras" | "review";

export const STEPS: Array<{ id: StepId; title: string; hint: string }> = [
  { id: "basics", title: "Asosiy", hint: "Kim siz va qanday ish qidiryapsiz" },
  { id: "education", title: "Ta’lim", hint: "Qayerda va nimani o‘qiyapsiz" },
  { id: "experience", title: "Tajriba", hint: "Amaliyot, ish, loyiha, ko‘ngillilik" },
  { id: "languages", title: "Tillar", hint: "Qaysi tillarni bilasiz" },
  { id: "extras", title: "Yutuqlar", hint: "Yutuqlar va havolalar" },
  { id: "review", title: "Ko‘rib chiqish", hint: "Ish beruvchi qanday ko‘radi" },
];

export interface Draft {
  headline: string;
  region: string;
  experience: CandidateWorkExperienceItem[];
  languages: CandidateLanguageItem[];
  achievements: CandidateAchievementItem[];
  education: CandidateEducationDetails;
  prefs: CandidateCareerPreferences;
}

export function toDraft(profile: CandidateProfileData | null, resume: CandidateResumeDetailsResponse): Draft {
  return {
    headline: profile?.headline ?? "",
    region: profile?.region ?? "",
    experience: resume.work_experiences ?? [],
    languages: resume.languages ?? [],
    achievements: resume.achievements ?? [],
    education: resume.education_details,
    prefs: resume.career_preferences,
  };
}

/** "2025-09-01" -> "2025-09" for <input type="month">; and back. */
export const toMonth = (iso?: string | null) => (iso ? iso.slice(0, 7) : "");
export const fromMonth = (month: string) => (month ? `${month}-01` : "");

export const emptyExperience = (): CandidateWorkExperienceItem => ({
  company_name: "",
  role_title: "",
  employment_type: "INTERNSHIP",
  location: "",
  start_date: "",
  end_date: null,
  is_current: false,
  description: "",
  technologies: [],
});

export const emptyAchievement = (): CandidateAchievementItem => ({
  title: "",
  category: "AWARD",
  issuer: "",
  awarded_date: null,
  description: "",
  url: null,
});

export type Errors = Record<string, string>;

export function validateExperience(w: CandidateWorkExperienceItem): Errors {
  const e: Errors = {};
  if (w.role_title.trim().length < 2) e.role_title = "Lavozimni yozing (kamida 2 belgi).";
  if (w.company_name.trim().length < 2) e.company_name = "Tashkilot nomini yozing.";
  if (!w.start_date) e.start_date = "Qachon boshlaganingizni tanlang.";
  if (!w.is_current && w.end_date && w.start_date && w.end_date < w.start_date) e.end_date = "Tugash sanasi boshlanishdan oldin bo‘lmasin.";
  return e;
}

export function validateAchievement(a: CandidateAchievementItem): Errors {
  const e: Errors = {};
  if (a.title.trim().length < 2) e.title = "Yutuq nomini yozing.";
  if (a.issuer.trim().length < 2) e.issuer = "Kim berganini yozing (tashkilot, tanlov).";
  return e;
}

export function validateStep(step: StepId, d: Draft): Errors {
  const e: Errors = {};
  if (step === "basics") {
    if (d.headline.trim().length < 3) e.headline = "Kasbiy sarlavhani yozing — ish beruvchilar sizni shu bo‘yicha qidiradi.";
    if (d.prefs.preferred_weekly_hours < 0 || d.prefs.preferred_weekly_hours > 60) e.hours = "Haftalik soat 0–60 oralig‘ida bo‘lsin.";
  }
  if (step === "languages") {
    d.languages.forEach((l, i) => {
      if (l.language.trim().length < 2) e[`lang_${i}`] = "Til nomini yozing.";
    });
  }
  return e;
}

/** Steps that look filled in enough for an employer (review checklist). */
export function completeness(d: Draft): Record<Exclude<StepId, "review">, boolean> {
  return {
    basics: d.headline.trim().length >= 3 && d.prefs.career_objective.trim().length >= 20 && d.prefs.desired_roles.length > 0,
    education: d.education.university_name.trim().length >= 2 && d.education.major.trim().length >= 2,
    experience: d.experience.length > 0,
    languages: d.languages.length > 0,
    extras: d.achievements.length > 0 || Boolean(d.prefs.github_username || d.prefs.linkedin_url),
  };
}

/** Total months of experience (overlaps counted once per month), for search filters. */
export function experienceMonths(items: CandidateWorkExperienceItem[], today = new Date()): number {
  const months = new Set<string>();
  for (const w of items) {
    if (!w.start_date) continue;
    const start = new Date(w.start_date);
    const end = w.is_current || !w.end_date ? today : new Date(w.end_date);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) continue;
    const cur = new Date(start.getFullYear(), start.getMonth(), 1);
    while (cur <= end && months.size < 600) {
      months.add(`${cur.getFullYear()}-${cur.getMonth()}`);
      cur.setMonth(cur.getMonth() + 1);
    }
  }
  return months.size;
}

const SAVE_ERRORS: Record<string, string> = {
  INVALID_COMPANY_NAME: "Tajribadagi tashkilot nomini to‘ldiring (2–200 belgi).",
  INVALID_POSITION: "Tajribadagi lavozimni to‘ldiring (2–200 belgi).",
  INVALID_WORK_DATE_RANGE: "Tajribada tugash sanasi boshlanishdan oldin bo‘lmasin.",
  INVALID_LANGUAGE_NAME: "Til nomini to‘ldiring.",
  INVALID_LANGUAGE_LEVEL: "Til darajasini tanlang.",
  INVALID_ACHIEVEMENT_TITLE: "Yutuq nomini to‘ldiring.",
  INVALID_ACHIEVEMENT_ISSUER: "Yutuqni kim berganini to‘ldiring.",
};

export function describeSaveError(err: unknown): string {
  const msg = err instanceof Error ? err.message : "";
  if (SAVE_ERRORS[msg]) return SAVE_ERRORS[msg];
  if (/^[A-Z0-9_]+$/.test(msg) || !msg) return "Saqlab bo‘lmadi. Internetni tekshirib, qayta urinib ko‘ring.";
  return msg;
}
