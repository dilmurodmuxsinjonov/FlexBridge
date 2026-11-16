import { Briefcase, GraduationCap, Languages, Target, Trophy } from "lucide-react";
import type { EmployerResumeView } from "@/lib/api";
import { ACHIEVEMENT_LABELS, LANGUAGE_LEVEL_LABELS, WORK_MODE_LABELS, WORK_TYPE_LABELS } from "@/lib/resumeContract";

function period(start?: string | null, end?: string | null, current?: boolean) {
  const fmt = (v?: string | null) => (v ? v.slice(0, 7).split("-").reverse().join(".") : "");
  if (!start) return "";
  return `${fmt(start)} — ${current || !end ? "hozirgacha" : fmt(end)}`;
}

function Section({ icon: Icon, title, children }: { icon: typeof Briefcase; title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h4 className="text-xs font-bold uppercase tracking-wide text-[var(--fb-ink-muted)] flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" aria-hidden="true" /> {title}
      </h4>
      {children}
    </section>
  );
}

/**
 * The resume exactly as an employer sees it (no phone, e-mail or Telegram).
 * Used in the employer candidate view and as the student's "how employers see me" preview.
 */
export default function ResumePreview({ resume }: { resume: EmployerResumeView | null | undefined }) {
  if (!resume) return null;
  const ed = resume.education_details || {};
  const cp = resume.career_preferences || {};
  const hasEducation = Boolean(ed.university_name || ed.faculty || ed.major);
  const empty =
    !hasEducation &&
    !cp.career_objective &&
    resume.work_experiences.length === 0 &&
    resume.languages.length === 0 &&
    resume.achievements.length === 0;

  if (empty) {
    return <p className="text-xs text-[var(--fb-ink-secondary)]">Nomzod hali rezyume bo‘limlarini to‘ldirmagan.</p>;
  }

  return (
    <div className="flex flex-col gap-5 text-sm">
      {(cp.career_objective || (cp.desired_roles && cp.desired_roles.length > 0)) && (
        <Section icon={Target} title="Maqsad">
          {cp.career_objective && <p className="text-[var(--fb-ink)]">{cp.career_objective}</p>}
          <div className="flex flex-wrap gap-1.5 text-xs">
            {(cp.desired_roles || []).map((r) => (
              <span key={r} className="px-2 py-0.5 rounded-full skeuo-badge-recessed">{r}</span>
            ))}
            {cp.preferred_work_mode && (
              <span className="px-2 py-0.5 rounded-full skeuo-badge-recessed">
                {WORK_MODE_LABELS[cp.preferred_work_mode] ?? cp.preferred_work_mode}
              </span>
            )}
            {cp.preferred_weekly_hours ? (
              <span className="px-2 py-0.5 rounded-full skeuo-badge-recessed">Haftasiga {cp.preferred_weekly_hours} soat</span>
            ) : null}
          </div>
        </Section>
      )}

      {resume.work_experiences.length > 0 && (
        <Section icon={Briefcase} title="Tajriba">
          <ul className="flex flex-col gap-3">
            {resume.work_experiences.map((w, i) => (
              <li key={`${w.company_name}-${i}`} className="border-l-2 border-[var(--fb-hairline)] pl-3">
                <div className="font-semibold text-[var(--fb-ink)]">
                  {w.position} · {w.company_name}
                </div>
                <div className="text-xs text-[var(--fb-ink-muted)]">
                  {[WORK_TYPE_LABELS[w.work_type] ?? w.work_type, w.location, period(w.start_date, w.end_date, w.is_current)]
                    .filter(Boolean)
                    .join(" · ")}
                </div>
                {w.responsibilities && <p className="text-xs text-[var(--fb-ink-secondary)] mt-1 whitespace-pre-line">{w.responsibilities}</p>}
                {w.technologies && w.technologies.length > 0 && (
                  <div className="text-[11px] text-[var(--fb-ink-muted)] mt-1">{w.technologies.join(", ")}</div>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {hasEducation && (
        <Section icon={GraduationCap} title="Ta’lim">
          <div className="text-[var(--fb-ink)]">
            {[ed.university_name, ed.faculty, ed.major].filter(Boolean).join(" · ")}
          </div>
          <div className="text-xs text-[var(--fb-ink-muted)]">
            {[ed.degree_level, ed.study_year && `${ed.study_year}-kurs`, ed.gpa && `GPA ${ed.gpa}`, ed.graduation_year && `Bitiradi: ${ed.graduation_year}`]
              .filter(Boolean)
              .join(" · ")}
          </div>
          {ed.thesis_topic && <div className="text-xs text-[var(--fb-ink-secondary)]">Mavzu: {ed.thesis_topic}</div>}
        </Section>
      )}

      {resume.languages.length > 0 && (
        <Section icon={Languages} title="Tillar">
          <div className="flex flex-wrap gap-1.5 text-xs">
            {resume.languages.map((l) => (
              <span key={l.language_name} className="px-2 py-0.5 rounded-full skeuo-badge-recessed">
                {l.language_name} — {LANGUAGE_LEVEL_LABELS[l.level] ?? l.level}
                {l.certificate_score ? ` (${l.certificate_score})` : ""}
              </span>
            ))}
          </div>
        </Section>
      )}

      {resume.achievements.length > 0 && (
        <Section icon={Trophy} title="Yutuqlar">
          <ul className="flex flex-col gap-1 text-xs">
            {resume.achievements.map((a, i) => (
              <li key={`${a.title}-${i}`}>
                <span className="font-semibold text-[var(--fb-ink)]">{a.title}</span>
                <span className="text-[var(--fb-ink-muted)]">
                  {" "}
                  · {ACHIEVEMENT_LABELS[a.category] ?? a.category} · {a.issuer}
                  {a.date ? ` · ${a.date.slice(0, 4)}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(cp.github_url || cp.linkedin_url || cp.website_url) && (
        <div className="flex flex-wrap gap-3 text-xs">
          {[cp.github_url, cp.linkedin_url, cp.website_url].filter(Boolean).map((url) => (
            <a key={url} href={url} target="_blank" rel="noopener noreferrer nofollow" className="underline text-[var(--fb-ink-secondary)]">
              {url!.replace(/^https?:\/\//, "")}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
