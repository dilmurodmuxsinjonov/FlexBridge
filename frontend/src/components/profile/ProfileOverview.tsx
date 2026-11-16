"use client";

import React from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Bell,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  Circle,
  Download,
  FileText,
  FolderGit2,
  GraduationCap,
  Loader2,
  PenLine,
  Plus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type {
  AvailabilityRuleItem,
  CandidateApplicationsSummary,
  CandidateEnrollmentItem,
  CandidateProfileSkill,
  CandidateWorkExperienceItem,
  CertificateItem,
  PortfolioItem,
} from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import { firstName, initials, isoWeekday, uzDate } from "@/lib/person";
import { experienceMonths } from "@/components/resume/resumeDraft";
import type { ClassSlot } from "@/lib/timetable";

export type OverviewTab = "PROFILE" | "SKILLS" | "AVAILABILITY" | "ENROLLMENTS" | "PORTFOLIO" | "CERTIFICATES";

export interface ProfileOverviewProps {
  name?: string | null;
  headline?: string | null;
  region?: string | null;
  skills: CandidateProfileSkill[];
  rules: AvailabilityRuleItem[];
  enrollments: CandidateEnrollmentItem[];
  portfolios: PortfolioItem[];
  certificates: CertificateItem[];
  experiences: CandidateWorkExperienceItem[];
  resumeUpdatedAt?: string | null;
  /** Official class timetable slots (drawn under the free-time bars). */
  classes?: ClassSlot[];
  applications: CandidateApplicationsSummary | null;
  applicationsError?: boolean;
  isExporting: boolean;
  onExport: () => void;
  onOpenTab: (tab: OverviewTab) => void;
  /** Injected for tests; defaults to now. */
  today?: Date;
}

const DAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];
const DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];
const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

/** Readiness items an employer actually looks at; each opens the tab that fixes it. */
export function readinessItems(p: Pick<ProfileOverviewProps, "headline" | "skills" | "rules" | "enrollments" | "experiences" | "portfolios">) {
  return [
    { key: "headline", label: "Rezyume sarlavhasi", done: (p.headline || "").trim().length >= 3, tab: "PROFILE" as const },
    { key: "skills", label: "Ko‘nikmalar", done: p.skills.length > 0, tab: "SKILLS" as const },
    { key: "rules", label: "Bo‘sh vaqt jadvali", done: p.rules.length > 0, tab: "AVAILABILITY" as const },
    { key: "student", label: "Talabalik tasdig‘i", done: p.enrollments.some((e) => e.status === "VERIFIED"), tab: "ENROLLMENTS" as const },
    { key: "work", label: "Tajriba yoki loyiha", done: p.experiences.length + p.portfolios.length > 0, tab: "PORTFOLIO" as const },
  ];
}

function WeekTimeline({ rules, classes = [], today, onEdit }: { rules: AvailabilityRuleItem[]; classes?: ClassSlot[]; today: Date; onEdit: () => void }) {
  const todayIdx = isoWeekday(today);
  const spans = [...rules, ...classes];
  const minStart = spans.length ? Math.min(...spans.map((r) => r.start_minute)) : 8 * 60;
  const maxEnd = spans.length ? Math.max(...spans.map((r) => r.end_minute)) : 20 * 60;
  const from = Math.max(0, Math.floor(Math.min(minStart, 8 * 60) / 60) * 60);
  const to = Math.min(24 * 60, Math.ceil(Math.max(maxEnd, 20 * 60) / 60) * 60);
  const span = to - from;
  const ticks: number[] = [];
  for (let m = from; m <= to; m += span > 12 * 60 ? 4 * 60 : 2 * 60) ticks.push(m);
  const totalMinutes = rules.reduce((sum, r) => sum + Math.max(0, r.end_minute - r.start_minute), 0);

  return (
    <section className="fb-panel skeuo-card p-5 sm:p-6 flex flex-col gap-4 min-w-0" aria-labelledby="fb-week-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="fb-week-title" className="text-base font-semibold text-[var(--fb-ink)]">Haftalik bo‘sh vaqtim</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">
            {rules.length
              ? `Ish uchun haftasiga ${Math.round((totalMinutes / 60) * 10) / 10} soat`
              : "Ish beruvchilar smenani shu jadvalga qarab taklif qiladi"}
          </p>
        </div>
        <button type="button" onClick={onEdit} className="fb-icon-btn-light fb-icon-btn h-9 w-9" aria-label="Jadvalni tahrirlash">
          <PenLine className="h-4 w-4" />
        </button>
      </div>

      {rules.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-[22px] skeuo-well px-4 py-10 text-center">
          <CalendarDays className="h-6 w-6 text-[var(--fb-ink-muted)]" aria-hidden="true" />
          <p className="max-w-xs text-xs text-[var(--fb-ink-secondary)]">
            Dars jadvalingizga to‘qnashmaydigan bo‘sh vaqtlarni belgilang.
          </p>
          <button type="button" onClick={onEdit} className="rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
            Jadvalni to‘ldirish
          </button>
        </div>
      ) : (
        <div className="min-w-0">
          <div>
            <div className="relative ml-10 h-5 text-[10px] text-[var(--fb-ink-muted)]" aria-hidden="true">
              {ticks.map((t) => (
                <span key={t} className="absolute -translate-x-1/2 tabular-nums" style={{ left: `${((t - from) / span) * 100}%` }}>
                  {hhmm(t)}
                </span>
              ))}
            </div>
            <ul className="flex flex-col gap-1.5">
              {DAYS.map((d, i) => {
                const weekday = i + 1;
                const dayRules = rules.filter((r) => r.weekday === weekday);
                const dayClasses = classes.filter((c) => c.weekday === weekday);
                const isToday = weekday === todayIdx;
                return (
                  <li key={d} className="flex items-center gap-2">
                    <span
                      className={`w-8 shrink-0 text-xs ${isToday ? "font-bold text-[var(--fb-ink)]" : "text-[var(--fb-ink-muted)]"}`}
                      title={DAY_NAMES[i]}
                    >
                      {d}
                    </span>
                    <div className="relative h-8 flex-1 rounded-full bg-[color-mix(in_srgb,var(--fb-well-deep)_40%,transparent)]">
                      {ticks.slice(1, -1).map((t) => (
                        <span
                          key={t}
                          aria-hidden="true"
                          className="absolute top-1/2 h-1 w-1 -translate-y-1/2 rounded-full bg-[color-mix(in_srgb,var(--fb-ink-muted)_30%,transparent)]"
                          style={{ left: `${((t - from) / span) * 100}%` }}
                        />
                      ))}
                      {dayClasses.map((c) => (
                        <span
                          key={`c${c.start_minute}`}
                          className="absolute top-1/2 h-2 -translate-y-1/2 rounded-full bg-[color-mix(in_srgb,var(--fb-ink-muted)_45%,transparent)]"
                          style={{ left: `${((c.start_minute - from) / span) * 100}%`, width: `${((c.end_minute - c.start_minute) / span) * 100}%` }}
                          title={`${DAY_NAMES[i]}: dars ${c.start_time}–${c.end_time}, ${c.subject_name}`}
                        />
                      ))}
                      {dayRules.map((r) => {
                        const left = ((r.start_minute - from) / span) * 100;
                        const width = Math.max(((r.end_minute - r.start_minute) / span) * 100, 6);
                        const label = `${hhmm(r.start_minute)}–${hhmm(r.end_minute)}`;
                        return (
                          <span
                            key={`${r.id ?? ""}${r.start_minute}`}
                            className={`fb-bar absolute top-0.5 bottom-0.5 flex items-center justify-center overflow-hidden px-2 text-[11px] font-semibold tabular-nums ${isToday ? "fb-bar-today" : ""}`}
                            style={{ left: `${left}%`, width: `${width}%` }}
                            title={`${DAY_NAMES[i]}: ${label}`}
                          >
                            <span className="truncate">{width > 20 ? label : ""}</span>
                          </span>
                        );
                      })}
                    </div>
                  </li>
                );
              })}
            </ul>
            <div className="mt-3 ml-10 flex flex-wrap items-center gap-4 text-[11px] text-[var(--fb-ink-muted)]">
              <span className="inline-flex items-center gap-1.5">
                <span className="fb-bar h-2.5 w-2.5" aria-hidden="true" /> Ish uchun bo‘sh
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="fb-bar fb-bar-today h-2.5 w-2.5" aria-hidden="true" /> Bugun
              </span>
              {classes.length > 0 && (
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-1.5 w-3 rounded-full bg-[color-mix(in_srgb,var(--fb-ink-muted)_45%,transparent)]" aria-hidden="true" /> Dars
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ReadinessCard(props: ProfileOverviewProps) {
  const items = readinessItems(props);
  const done = items.filter((i) => i.done).length;
  const pct = Math.round((done / items.length) * 100);
  return (
    <section className="fb-panel skeuo-card p-5 sm:p-6 flex flex-col gap-4" aria-labelledby="fb-ready-title">
      <h2 id="fb-ready-title" className="text-base font-semibold text-[var(--fb-ink)]">Profil tayyorligi</h2>
      <div>
        <p className="font-display text-5xl font-bold tracking-tight text-[var(--fb-ink)] tabular-nums">
          {pct}
          <span className="text-2xl align-top">%</span>
        </p>
        <p className="mt-1 text-xs text-[var(--fb-ink-muted)]">
          {items.length} tadan {done} bo‘lim tayyor
        </p>
      </div>
      <div className="flex gap-1" role="img" aria-label={`${items.length} bo‘limdan ${done} tasi tayyor`}>
        {items.map((i) => (
          <span key={i.key} className={`h-2 flex-1 rounded-full ${i.done ? "bg-[var(--fb-ink)]" : "bg-[var(--fb-well-deep)]"}`} />
        ))}
      </div>
      <ul className="flex flex-col gap-1">
        {items.map((i) => (
          <li key={i.key}>
            <button
              type="button"
              onClick={() => props.onOpenTab(i.tab)}
              className="flex w-full items-center justify-between gap-2 rounded-xl px-2 py-1.5 text-left text-xs hover:bg-[var(--fb-well-deep)]"
            >
              <span className="inline-flex items-center gap-2 text-[var(--fb-ink-secondary)]">
                {i.done ? (
                  <CheckCircle2 className="h-4 w-4 text-[var(--fb-ink)]" aria-hidden="true" />
                ) : (
                  <Circle className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
                )}
                {i.label}
              </span>
              <span className={i.done ? "text-[var(--fb-ink-muted)]" : "font-semibold text-[var(--fb-ink)]"}>
                {i.done ? "Tayyor" : "To‘ldirish"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ResumeCard({ name, headline, resumeUpdatedAt, isExporting, onExport, onOpenTab }: ProfileOverviewProps) {
  const updated = resumeUpdatedAt ? new Date(resumeUpdatedAt) : null;
  return (
    <section data-skeuo-dark="true" className="fb-ink-card relative overflow-hidden p-5 sm:p-6 flex flex-col gap-4" aria-labelledby="fb-resume-title">
      <div className="flex items-center justify-between">
        <h2 id="fb-resume-title" className="text-base font-semibold">Rezyume</h2>
        <Sparkles className="h-4 w-4 fb-muted" aria-hidden="true" />
      </div>
      <div className="relative mx-auto my-1 h-40 w-40 sm:h-44 sm:w-44" aria-hidden="true">
        <div className="fb-ring absolute inset-0" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold">{headline?.trim() || "Sarlavha hali yozilmagan"}</p>
        <p className="text-xs fb-muted">
          PDF · {updated && !Number.isNaN(updated.getTime()) ? `yangilangan ${updated.toLocaleDateString("uz-UZ")}` : "ish beruvchi ko‘radigan ko‘rinish"}
        </p>
      </div>
      <div className="flex items-center gap-2.5">
        <span className="fb-avatar h-8 w-8 text-[11px]" aria-hidden="true">{initials(name)}</span>
        <span className="min-w-0 flex-1 truncate text-xs fb-muted">{name?.trim() || "Mening hisobim"}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onExport}
          disabled={isExporting}
          className="inline-flex items-center justify-center gap-1.5 rounded-full bg-white px-3 py-2 text-xs font-semibold text-[#0c0d10] disabled:opacity-60"
        >
          {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          <span>Yuklab olish</span>
        </button>
        <button
          type="button"
          onClick={() => onOpenTab("PROFILE")}
          className="inline-flex items-center justify-center gap-1.5 rounded-full border border-white/20 px-3 py-2 text-xs font-semibold text-white hover:bg-white/10"
        >
          <PenLine className="h-3.5 w-3.5" />
          <span>Tahrirlash</span>
        </button>
      </div>
    </section>
  );
}

function DocumentsCard({ portfolios, certificates, onOpenTab }: ProfileOverviewProps) {
  const rows = [
    ...certificates.map((c) => ({
      id: `c-${c.id}`,
      title: c.file_name || c.title,
      meta: [c.issuer, c.issue_date?.slice(0, 4)].filter(Boolean).join(" · "),
      tab: "CERTIFICATES" as const,
    })),
    ...portfolios.map((p) => ({
      id: `p-${p.id}`,
      title: p.title,
      meta: p.skills.slice(0, 2).join(", ") || "Loyiha",
      tab: "PORTFOLIO" as const,
    })),
  ];
  return (
    <section className="fb-panel skeuo-card p-5 sm:p-6 flex flex-col gap-4" aria-labelledby="fb-docs-title">
      <div className="flex items-center justify-between">
        <h2 id="fb-docs-title" className="text-base font-semibold text-[var(--fb-ink)]">Hujjatlarim</h2>
        <button type="button" onClick={() => onOpenTab("CERTIFICATES")} className="fb-icon-btn h-9 w-9" aria-label="Sertifikat qo‘shish">
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-[18px] skeuo-well px-4 py-6 text-center text-xs text-[var(--fb-ink-secondary)]">
          Sertifikat yoki loyiha qo‘shing — ular rezyumeingizga ilova qilinadi.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.slice(0, 4).map((r) => (
            <li key={r.id}>
              <button type="button" onClick={() => onOpenTab(r.tab)} className="fb-file-row w-full text-left">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--fb-card-top)] shadow-sm">
                  {r.tab === "PORTFOLIO" ? <FolderGit2 className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-[var(--fb-ink)]">{r.title}</span>
                  {r.meta && <span className="block truncate text-[11px] text-[var(--fb-ink-muted)]">{r.meta}</span>}
                </span>
              </button>
            </li>
          ))}
          {rows.length > 4 && <li className="px-1 text-[11px] text-[var(--fb-ink-muted)]">va yana {rows.length - 4} ta</li>}
        </ul>
      )}
    </section>
  );
}

function ApplicationsStrip({ applications, applicationsError }: ProfileOverviewProps) {
  const a = applications;
  const total = a?.total_applications ?? 0;
  const stats = a
    ? [
        { label: "Jami arizalar", value: total, of: total },
        { label: "Ko‘rib chiqilmoqda", value: a.submitted + a.under_review, of: total },
        { label: "Suhbat", value: a.interview_scheduled, of: total },
        { label: "Taklif", value: a.offered + a.accepted, of: total },
      ]
    : [];
  return (
    <section className="fb-panel skeuo-card p-5 sm:px-6 flex flex-col gap-4 lg:flex-row lg:items-center" aria-labelledby="fb-apps-title">
      <div className="flex items-center justify-between gap-3 lg:w-40 lg:shrink-0 lg:flex-col lg:items-start">
        <h2 id="fb-apps-title" className="text-base font-semibold text-[var(--fb-ink)]">Arizalarim</h2>
        <Link href="/nomzod/arizalar" className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]">
          Barchasi <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>
      {applicationsError ? (
        <p className="text-xs text-[var(--fb-ink-muted)]">Arizalar statistikasini hozir yuklab bo‘lmadi.</p>
      ) : !a ? (
        <div className="grid flex-1 grid-cols-2 gap-4 sm:grid-cols-4" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-12 animate-pulse rounded-2xl bg-[var(--fb-well-deep)]" />
          ))}
        </div>
      ) : (
        <dl className="grid flex-1 grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="min-w-0">
              <dt className="truncate text-[11px] text-[var(--fb-ink-muted)]">{s.label}</dt>
              <dd className="mt-0.5 flex items-center gap-2">
                <span className="text-2xl font-bold tabular-nums text-[var(--fb-ink)]">{s.value}</span>
                <span className="fb-progress flex-1" aria-hidden="true">
                  <span style={{ width: `${s.of ? Math.round((s.value / s.of) * 100) : 0}%` }} />
                </span>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

function CareerPanel({ skills, experiences, portfolios, enrollments, onOpenTab }: ProfileOverviewProps) {
  const verified = skills.filter((s) => s.verified).length;
  const months = experienceMonths(experiences);
  const enrollment = enrollments.find((e) => e.status === "VERIFIED") ?? enrollments[0] ?? null;
  const stepIdx = !enrollment ? 0 : enrollment.status === "VERIFIED" ? 3 : enrollment.status === "DECLARED" ? 1 : 2;

  const column = "flex flex-col gap-3 min-w-0 p-5 sm:p-6";
  return (
    <section data-skeuo-dark="true" className="fb-ink-card grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-white/10" aria-label="Kasbiy ko‘rsatkichlar">
      <div className={column}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">Ko‘nikmalar</h3>
            <p className="text-xs fb-muted">Ish beruvchi qidiruvi shu bo‘yicha</p>
          </div>
          <button type="button" onClick={() => onOpenTab("SKILLS")} className="text-xs fb-muted hover:text-white" aria-label="Ko‘nikmalarni ochish">
            <ArrowUpRight className="h-4 w-4" />
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5 min-h-[28px]">
          {skills.slice(0, 4).map((s) => (
            <span key={s.skill_id} className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-medium">
              {s.name_uz || s.code}
            </span>
          ))}
          {skills.length === 0 && <span className="text-xs fb-muted">Hali qo‘shilmagan</span>}
        </div>
        <div className="mt-auto">
          <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
            <span>Tasdiqlangan</span>
            <span className="tabular-nums">{verified}/{skills.length}</span>
          </div>
          <div className="fb-progress"><span style={{ width: `${skills.length ? (verified / skills.length) * 100 : 0}%` }} /></div>
        </div>
        <div className="flex items-center gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> {skills.length}</span>
          <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> {verified}</span>
        </div>
      </div>

      <div className={column}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">Tajriba</h3>
            <p className="text-xs fb-muted">Amaliyot, ish va loyihalar</p>
          </div>
          <button type="button" onClick={() => onOpenTab("PORTFOLIO")} className="text-xs fb-muted hover:text-white" aria-label="Portfolioni ochish">
            <ArrowUpRight className="h-4 w-4" />
          </button>
        </div>
        <p className="font-display text-3xl font-bold tabular-nums">
          {months >= 12 ? `${Math.floor(months / 12)} yil ${months % 12 ? `${months % 12} oy` : ""}` : `${months} oy`}
        </p>
        <p className="text-xs fb-muted -mt-2">umumiy tajriba</p>
        <div className="mt-auto flex items-center gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><BriefcaseBusiness className="h-3.5 w-3.5" /> {experiences.length} ish joyi</span>
          <span className="inline-flex items-center gap-1.5"><FolderGit2 className="h-3.5 w-3.5" /> {portfolios.length} loyiha</span>
        </div>
      </div>

      <div className={column}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold">Talabalik</h3>
            <p className="truncate text-xs fb-muted">{enrollment?.institution_name || "OTM tasdig‘i"}</p>
          </div>
          <button type="button" onClick={() => onOpenTab("ENROLLMENTS")} className="text-xs fb-muted hover:text-white" aria-label="Talabalik bo‘limini ochish">
            <ArrowUpRight className="h-4 w-4" />
          </button>
        </div>
        <p className="text-sm font-semibold">{enrollment ? enumLabel(enrollment.status) : "Hali yuborilmagan"}</p>
        <div className="mt-auto">
          <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
            <span>Ariza → tekshiruv → tasdiq</span>
            <span className="tabular-nums">{stepIdx}/3</span>
          </div>
          <div className="fb-progress"><span style={{ width: `${(stepIdx / 3) * 100}%` }} /></div>
        </div>
        <div className="flex items-center gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><GraduationCap className="h-3.5 w-3.5" /> {enrollment?.program || "Yo‘nalish ko‘rsatilmagan"}</span>
        </div>
      </div>
    </section>
  );
}

/** Bento overview of the candidate's own profile (design prototype, LOG-179). */
export default function ProfileOverview(props: ProfileOverviewProps) {
  const today = props.today ?? new Date();
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-[var(--fb-ink-muted)]">Salom, {firstName(props.name)}</p>
          <h1 className="fb-display mt-1">Mening profilim</h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--fb-ink-secondary)]">
            {[props.headline?.trim(), props.region?.trim()].filter(Boolean).join(" · ") ||
              "Rezyume, jadval va hujjatlaringiz bitta joyda — ish beruvchilar sizni shular orqali topadi."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="fb-capsule inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
            {uzDate(today)}
          </span>
          <Link href="/nomzod/bildirishnomalar" className="fb-icon-btn" aria-label="Bildirishnomalar">
            <Bell className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <WeekTimeline rules={props.rules} classes={props.classes} today={today} onEdit={() => props.onOpenTab("AVAILABILITY")} />
        <ReadinessCard {...props} />
        <ResumeCard {...props} />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,2.6fr)]">
        <DocumentsCard {...props} />
        <div className="flex min-w-0 flex-col gap-5">
          <ApplicationsStrip {...props} />
          <CareerPanel {...props} />
        </div>
      </div>
    </div>
  );
}
