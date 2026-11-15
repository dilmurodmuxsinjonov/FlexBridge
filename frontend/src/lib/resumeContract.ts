/**
 * Mapping between the resume builder UI shape and the backend contract
 * (`/api/v1/me/candidate/resume-details`, candidate_resume_builder.py).
 *
 * The UI used different field names (role_title, language, proficiency, ...)
 * than the backend (position, language_name, level, ...). Saving any work
 * experience or language therefore failed with 422, and unknown enum values
 * were silently coerced (e.g. "Loyiha" became "Amaliyot"). Every request and
 * response now goes through these two functions.
 */
import type {
  CandidateAchievementItem,
  CandidateCareerPreferences,
  CandidateEducationDetails,
  CandidateLanguageItem,
  CandidateWorkExperienceItem,
} from "./api";

export const WORK_TYPE_LABELS: Record<string, string> = {
  INTERNSHIP: "Amaliyot",
  PART_TIME: "Part-time",
  FULL_TIME: "To‘liq stavka",
  PROJECT: "Shartnoma / Loyiha",
  FREELANCE: "Frilans",
  VOLUNTEER: "Ko‘ngillilik",
};

export const ACHIEVEMENT_LABELS: Record<string, string> = {
  OLYMPIAD: "Fan olimpiadasi",
  HACKATHON: "Hakaton / IT tanlov",
  SCHOLARSHIP: "Stipendiya / Grant",
  PUBLICATION: "Ilmiy maqola / Patent",
  AWARD: "Mukofot",
  COMPETITION: "Tanlov",
  OTHER: "Boshqa",
};

export const LANGUAGE_LEVEL_LABELS: Record<string, string> = {
  NATIVE: "Ona tili",
  C2: "C2 (Mukammal)",
  C1: "C1 (Ilg‘or)",
  B2: "B2 (Mustaqil)",
  B1: "B1 (O‘rta)",
  A2: "A2 (Boshlang‘ich+)",
  A1: "A1 (Boshlang‘ich)",
};

export const WORK_MODE_LABELS: Record<string, string> = {
  ONSITE: "Ofisda",
  REMOTE: "Masofaviy",
  HYBRID: "Gibrid",
  FLEXIBLE: "Moslashuvchan",
};

type Raw = Record<string, unknown>;

const str = (v: unknown) => (typeof v === "string" ? v : v == null ? "" : String(v));
const strOrNull = (v: unknown) => {
  const s = str(v).trim();
  return s ? s : null;
};
const num = (v: unknown, fallback: number) => {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
};
const list = (v: unknown) => (Array.isArray(v) ? v.map(str).map((s) => s.trim()).filter(Boolean) : []);

function githubUsername(url: string) {
  const m = url.match(/github\.com\/([^/?#]+)/i);
  return m ? m[1] : url;
}

function githubUrl(username: string) {
  const u = username.trim();
  if (!u) return "";
  return /^https?:\/\//i.test(u) ? u : `https://github.com/${u.replace(/^@/, "")}`;
}

/** "IELTS 7.0" -> { certificate_name: "IELTS", score: "7.0" } (best effort, lossless back). */
function splitCertificate(value: unknown) {
  const s = str(value).trim();
  if (!s) return { certificate_name: null, score: null };
  const m = s.match(/^(.*?)\s+([\d.,]+(?:\s*\/\s*[\d.,]+)?)$/);
  return m ? { certificate_name: m[1] || null, score: m[2] } : { certificate_name: s, score: null };
}

export function fromBackendResume(raw: Raw) {
  const ed = (raw.education_details ?? {}) as Raw;
  const cp = (raw.career_preferences ?? {}) as Raw;
  return {
    achievements: (Array.isArray(raw.achievements) ? raw.achievements : []).map((a: Raw): CandidateAchievementItem => ({
      id: str(a.id) || undefined,
      title: str(a.title),
      category: str(a.category) || "AWARD",
      issuer: str(a.issuer),
      awarded_date: strOrNull(a.date),
      description: str(a.description),
      url: strOrNull(a.url),
    })),
    work_experiences: (Array.isArray(raw.work_experiences) ? raw.work_experiences : []).map(
      (w: Raw): CandidateWorkExperienceItem => ({
        id: str(w.id) || undefined,
        company_name: str(w.company_name),
        role_title: str(w.position),
        employment_type: str(w.work_type) || "INTERNSHIP",
        location: str(w.location),
        start_date: str(w.start_date),
        end_date: strOrNull(w.end_date),
        is_current: Boolean(w.is_current),
        description: str(w.responsibilities),
        technologies: list(w.technologies),
      })
    ),
    languages: (Array.isArray(raw.languages) ? raw.languages : []).map((l: Raw): CandidateLanguageItem => ({
      id: str(l.id) || undefined,
      language: str(l.language_name),
      proficiency: str(l.level) || "B2",
      ...splitCertificate(l.certificate_score),
    })),
    education_details: {
      university_name: str(ed.university_name),
      faculty: str(ed.faculty),
      major: str(ed.major),
      degree_level: str(ed.degree_level) || "BAKALAVR",
      study_year: num(ed.study_year, 1),
      gpa: str(ed.gpa),
      graduation_year: num(ed.graduation_year, new Date().getFullYear() + 1),
      thesis_or_research_topic: str(ed.thesis_topic),
    } satisfies CandidateEducationDetails,
    career_preferences: {
      desired_roles: list(cp.desired_roles),
      work_mode: str(cp.preferred_work_mode) || "FLEXIBLE",
      preferred_weekly_hours: num(cp.preferred_weekly_hours, 20),
      expected_stipend_uzs: num(cp.desired_salary_uzs, 0),
      career_objective: str(cp.career_objective),
      linkedin_url: str(cp.linkedin_url),
      telegram_username: str(cp.telegram_username),
      github_username: githubUsername(str(cp.github_url)),
    } satisfies CandidateCareerPreferences,
  };
}

export function toBackendResume(ui: {
  achievements?: CandidateAchievementItem[];
  work_experiences?: CandidateWorkExperienceItem[];
  languages?: CandidateLanguageItem[];
  education_details?: Partial<CandidateEducationDetails>;
  career_preferences?: Partial<CandidateCareerPreferences>;
}) {
  const out: Raw = {};
  if (ui.achievements) {
    out.achievements = ui.achievements.map((a) => ({
      id: a.id,
      title: a.title,
      category: a.category,
      issuer: a.issuer,
      date: a.awarded_date ?? null,
      description: a.description ?? "",
      url: a.url ?? null,
    }));
  }
  if (ui.work_experiences) {
    out.work_experiences = ui.work_experiences.map((w) => ({
      id: w.id,
      company_name: w.company_name,
      position: w.role_title,
      work_type: w.employment_type,
      location: w.location ?? "",
      start_date: w.start_date || null,
      end_date: w.end_date ?? null,
      is_current: Boolean(w.is_current),
      responsibilities: w.description ?? "",
      technologies: w.technologies ?? [],
    }));
  }
  if (ui.languages) {
    out.languages = ui.languages.map((l) => ({
      id: l.id,
      language_name: l.language,
      level: l.proficiency,
      certificate_score: [l.certificate_name, l.score].filter(Boolean).join(" ") || null,
    }));
  }
  if (ui.education_details) {
    const ed = ui.education_details;
    out.education_details = {
      university_name: ed.university_name ?? "",
      faculty: ed.faculty ?? "",
      major: ed.major ?? "",
      degree_level: ed.degree_level ?? "",
      study_year: ed.study_year != null ? String(ed.study_year) : "",
      gpa: ed.gpa ?? "",
      graduation_year: ed.graduation_year != null ? String(ed.graduation_year) : "",
      thesis_topic: ed.thesis_or_research_topic ?? "",
      courses: [],
    };
  }
  if (ui.career_preferences) {
    const cp = ui.career_preferences;
    out.career_preferences = {
      desired_roles: cp.desired_roles ?? [],
      preferred_work_mode: cp.work_mode ?? "FLEXIBLE",
      preferred_weekly_hours: cp.preferred_weekly_hours ?? null,
      desired_salary_uzs: cp.expected_stipend_uzs ?? null,
      career_objective: cp.career_objective ?? "",
      linkedin_url: cp.linkedin_url ?? "",
      telegram_username: cp.telegram_username ?? "",
      github_url: githubUrl(cp.github_username ?? ""),
    };
  }
  return out;
}
