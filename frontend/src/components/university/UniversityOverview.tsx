"use client";

import React from "react";
import { ArrowUpRight, CalendarDays, CheckCircle2, FileCheck, GraduationCap, Plus, UserPlus, Users } from "lucide-react";
import type {
  AcademicReviewQueueItem,
  CoordinatorAssignmentQueueItem,
  TeacherAcademicAssignmentItem,
  UniversityTimetableResponse,
} from "@/lib/api";
import { firstName, initials, uzDate } from "@/lib/person";
import CountUp from "@/components/motion/CountUp";

export type UniversityTab = "queue" | "assignments" | "coordinator" | "enrollments" | "exports" | "analytics" | "timetable" | "documents" | "staff";

export interface UniversityOverviewProps {
  name?: string | null;
  institutionName?: string | null;
  institutionRegion?: string | null;
  isCoordinator: boolean;
  queue: AcademicReviewQueueItem[];
  queueError?: string | null;
  assignments: TeacherAcademicAssignmentItem[];
  coordinatorQueue: CoordinatorAssignmentQueueItem[];
  teachersCount: number;
  timetable: UniversityTimetableResponse | null;
  onOpen: (tab: UniversityTab) => void;
  /** Injected for tests; defaults to now. */
  today?: Date;
}

const DAY = 86_400_000;
const SHORT = ["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"];
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** Queue items per submission day for the last 7 days (oldest first). Older ones land on day 0. */
export function queueByDay(queue: AcademicReviewQueueItem[], today: Date) {
  const end = startOfDay(today).getTime();
  const days = Array.from({ length: 7 }, (_, i) => ({ date: new Date(end - (6 - i) * DAY), count: 0 }));
  for (const q of queue) {
    const t = new Date(q.submitted_at || q.local_date).getTime();
    if (Number.isNaN(t)) continue;
    const idx = Math.max(0, 6 - Math.floor((end - startOfDay(new Date(t)).getTime()) / DAY));
    days[Math.min(6, idx)].count += 1;
  }
  return days;
}

/** Whole days the oldest queued diary has been waiting. */
export function oldestWaitDays(queue: AcademicReviewQueueItem[], today: Date): number | null {
  const times = queue.map((q) => new Date(q.submitted_at || q.local_date).getTime()).filter((t) => !Number.isNaN(t));
  if (!times.length) return null;
  return Math.max(0, Math.floor((startOfDay(today).getTime() - startOfDay(new Date(Math.min(...times))).getTime()) / DAY));
}

function QueueFlow({ queue, queueError, onOpen, today }: UniversityOverviewProps & { today: Date }) {
  const days = queueByDay(queue, today);
  const max = Math.max(1, ...days.map((d) => d.count));
  const wait = oldestWaitDays(queue, today);
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="uni-flow">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="uni-flow" className="text-base font-semibold text-[var(--fb-ink)]">Kundaliklar oqimi</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">Ko‘rik kutayotganlar, yuborilgan kuni bo‘yicha</p>
        </div>
        <button type="button" onClick={() => onOpen("queue")} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Navbatni ochish">
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
      {queueError ? (
        <p className="text-sm text-[var(--fb-ink-secondary)]">Navbatni yuklab bo‘lmadi.</p>
      ) : (
        <>
          <div className="flex h-36 items-end gap-2" role="img" aria-label={`So‘nggi 7 kunda ${queue.length} ta kundalik kutmoqda`}>
            {days.map((d, i) => (
              <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
                <span className="text-[11px] font-semibold tabular-nums text-[var(--fb-ink)]">{d.count || ""}</span>
                <span
                  className={`w-full max-w-[34px] rounded-full ${d.count ? (i === 6 ? "fb-bar fb-bar-today" : "fb-bar") : "bg-[var(--fb-well-deep)]"}`}
                  style={{ height: `${d.count ? Math.max(14, (d.count / max) * 100) : 8}%` }}
                />
                <span className={`text-[11px] ${i === 6 ? "font-bold text-[var(--fb-ink)]" : "text-[var(--fb-ink-muted)]"}`}>{SHORT[d.date.getDay()]}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-[var(--fb-ink-secondary)]">
            {queue.length === 0
              ? "Navbat bo‘sh — hamma kundaliklar ko‘rib chiqilgan."
              : `Jami ${queue.length} ta · eng eskisi ${wait === 0 ? "bugun" : `${wait} kundan beri`} kutmoqda`}
          </p>
        </>
      )}
    </section>
  );
}

function CoverageCard({ isCoordinator, assignments, coordinatorQueue, onOpen }: UniversityOverviewProps) {
  const accepted = assignments.filter((a) => a.accepted_at).length;
  const parts = isCoordinator
    ? { done: assignments.length, wait: coordinatorQueue.length, doneLabel: "Rahbar biriktirilgan", waitLabel: "Rahbar kutmoqda", title: "Biriktiruv qamrovi", tab: "coordinator" as const }
    : { done: accepted, wait: assignments.length - accepted, doneLabel: "Qabul qilingan", waitLabel: "Qabul kutmoqda", title: "Mening talabalarim", tab: "assignments" as const };
  const total = parts.done + parts.wait;
  const pct = total ? Math.round((parts.done / total) * 100) : 0;
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="uni-cover">
      <h2 id="uni-cover" className="text-base font-semibold text-[var(--fb-ink)]">{parts.title}</h2>
      <p className="font-display text-5xl font-bold tracking-tight tabular-nums text-[var(--fb-ink)]">
        {total ? <CountUp value={pct} /> : "—"}
        {total > 0 && <span className="align-top text-2xl">%</span>}
      </p>
      <div className="flex h-2 gap-1" aria-hidden="true">
        <span className="rounded-full bg-[var(--fb-ink)]" style={{ flex: parts.done || 0.0001 }} />
        <span className="rounded-full bg-[var(--fb-well-deep)]" style={{ flex: parts.wait || (total ? 0.0001 : 1) }} />
      </div>
      <ul className="flex flex-col gap-2 text-xs">
        <li className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 text-[var(--fb-ink-secondary)]"><span className="h-2.5 w-2.5 rounded-full bg-[var(--fb-ink)]" />{parts.doneLabel}</span>
          <span className="font-semibold tabular-nums">{parts.done}</span>
        </li>
        <li className="flex items-center justify-between">
          <span className="inline-flex items-center gap-2 text-[var(--fb-ink-secondary)]"><span className="h-2.5 w-2.5 rounded-full bg-[var(--fb-well-deep)] ring-1 ring-[var(--fb-hairline)]" />{parts.waitLabel}</span>
          <span className="font-semibold tabular-nums">{parts.wait}</span>
        </li>
      </ul>
      <button type="button" onClick={() => onOpen(parts.tab)} className="mt-auto inline-flex w-fit items-center gap-1 text-xs font-semibold text-[var(--fb-ink-secondary)] hover:text-[var(--fb-ink)]">
        Ochish <ArrowUpRight className="h-3.5 w-3.5" />
      </button>
    </section>
  );
}

function NextReviewCard({ queue, onOpen, today }: UniversityOverviewProps & { today: Date }) {
  const oldest = [...queue].sort((a, b) => (a.submitted_at || a.local_date).localeCompare(b.submitted_at || b.local_date))[0];
  const wait = oldestWaitDays(queue, today);
  return (
    <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="uni-next">
      <div className="flex items-center justify-between">
        <h2 id="uni-next" className="text-sm font-semibold fb-muted">Navbatdagi ko‘rik</h2>
        <FileCheck className="h-4 w-4 fb-muted" aria-hidden="true" />
      </div>
      {oldest ? (
        <>
          <div className="flex items-center gap-3">
            <span className="fb-avatar h-12 w-12 text-sm" aria-hidden="true">{initials(oldest.student_name)}</span>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold">{oldest.student_name}</p>
              <p className="text-xs fb-muted tabular-nums">{oldest.local_date} kundaligi · {oldest.revision}-tahrir</p>
            </div>
          </div>
          <p className="text-xs fb-muted">{wait === 0 ? "Bugun yuborilgan" : `${wait} kundan beri kutmoqda`}</p>
          <button type="button" onClick={() => onOpen("queue")} className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-full bg-white px-4 py-2.5 text-xs font-semibold text-[#0c0d10]">
            Ko‘rib chiqish <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </>
      ) : (
        <div className="flex flex-1 flex-col justify-center gap-2">
          <CheckCircle2 className="h-7 w-7" aria-hidden="true" />
          <p className="text-lg font-semibold">Hammasi ko‘rib chiqilgan</p>
          <p className="text-xs fb-muted">Yangi kundalik kelsa, shu yerda ko‘rinadi.</p>
        </div>
      )}
    </section>
  );
}

function PeopleCard({ isCoordinator, coordinatorQueue, assignments, onOpen }: UniversityOverviewProps) {
  const rows = isCoordinator
    ? coordinatorQueue.map((c) => ({ id: c.id, name: c.student_name, meta: "Ilmiy rahbar kutmoqda" }))
    : assignments.map((a) => ({ id: a.id, name: a.student_name || "Talaba", meta: a.organization_name || (a.accepted_at ? "Nazoratda" : "Qabul kutmoqda") }));
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="uni-people">
      <div className="flex items-center justify-between">
        <h2 id="uni-people" className="text-base font-semibold text-[var(--fb-ink)]">{isCoordinator ? "Rahbar tayinlash" : "Talabalarim"}</h2>
        <button
          type="button"
          onClick={() => onOpen(isCoordinator ? "coordinator" : "assignments")}
          className="fb-icon-btn h-9 w-9"
          aria-label={isCoordinator ? "Rahbar tayinlash bo‘limini ochish" : "Talabalar ro‘yxatini ochish"}
        >
          {isCoordinator ? <UserPlus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        </button>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-[18px] skeuo-well px-4 py-6 text-center text-xs text-[var(--fb-ink-secondary)]">
          {isCoordinator ? "Rahbar kutayotgan talaba yo‘q." : "Sizga hali talaba biriktirilmagan."}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.slice(0, 4).map((r) => (
            <li key={r.id} className="fb-file-row">
              <span className="fb-avatar h-8 w-8 text-[11px]" aria-hidden="true">{initials(r.name)}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold text-[var(--fb-ink)]">{r.name}</span>
                <span className="block truncate text-[11px] text-[var(--fb-ink-muted)]">{r.meta}</span>
              </span>
            </li>
          ))}
          {rows.length > 4 && <li className="px-1 text-[11px] text-[var(--fb-ink-muted)]">va yana {rows.length - 4} ta</li>}
        </ul>
      )}
    </section>
  );
}

function CountsStrip({ queue, assignments, coordinatorQueue, teachersCount, isCoordinator }: UniversityOverviewProps) {
  const stats = [
    { label: "Ko‘rik navbati", value: queue.length },
    { label: "Nazoratdagi amaliyot", value: assignments.length },
    ...(isCoordinator ? [{ label: "Rahbar kutmoqda", value: coordinatorQueue.length }, { label: "O‘qituvchilar", value: teachersCount }] : []),
  ];
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:px-6 lg:flex-row lg:items-center" aria-labelledby="uni-today">
      <h2 id="uni-today" className="text-base font-semibold text-[var(--fb-ink)] lg:w-36 lg:shrink-0">Bugungi holat</h2>
      <dl className={`grid flex-1 grid-cols-2 gap-x-6 gap-y-4 ${stats.length > 2 ? "sm:grid-cols-4" : ""}`}>
        {stats.map((s) => (
          <div key={s.label} className="min-w-0">
            <dt className="truncate text-[11px] text-[var(--fb-ink-muted)]">{s.label}</dt>
            <dd className="mt-0.5 text-2xl font-bold tabular-nums text-[var(--fb-ink)]">{s.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function InkPanel({ assignments, coordinatorQueue, teachersCount, timetable, isCoordinator, onOpen }: UniversityOverviewProps) {
  const accepted = assignments.filter((a) => a.accepted_at).length;
  const col = "flex min-w-0 flex-col gap-3 p-5 sm:p-6";
  const head = (title: string, sub: string, tab: UniversityTab, label: string) => (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="truncate text-xs fb-muted">{sub}</p>
      </div>
      <button type="button" onClick={() => onOpen(tab)} className="fb-muted hover:text-white" aria-label={label}>
        <ArrowUpRight className="h-4 w-4" />
      </button>
    </div>
  );
  return (
    <section data-skeuo-dark="true" className="fb-ink-card grid grid-cols-1 divide-y divide-white/10 md:grid-cols-3 md:divide-x md:divide-y-0" aria-label="Akademik ko‘rsatkichlar">
      <div className={col}>
        {head("Amaliyot nazorati", "O‘qituvchi rahbarligidagi talabalar", "assignments", "Amaliyotlarni ochish")}
        <p className="font-display text-3xl font-bold tabular-nums"><CountUp value={assignments.length} /></p>
        <div className="mt-auto">
          <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
            <span>Rahbar qabul qilgan</span>
            <span className="tabular-nums">{accepted}/{assignments.length}</span>
          </div>
          <div className="fb-progress"><span style={{ width: `${assignments.length ? (accepted / assignments.length) * 100 : 0}%` }} /></div>
        </div>
      </div>
      <div className={col}>
        {head("Kafedra", isCoordinator ? "Rahbar tayinlash va xodimlar" : "Faqat koordinatorga ochiq", isCoordinator ? "coordinator" : "staff", "Kafedra bo‘limini ochish")}
        <p className="font-display text-3xl font-bold tabular-nums">{isCoordinator ? <CountUp value={coordinatorQueue.length} /> : "—"}</p>
        <p className="-mt-2 text-xs fb-muted">rahbar kutayotgan talaba</p>
        <div className="mt-auto flex items-center gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> {teachersCount} o‘qituvchi</span>
        </div>
      </div>
      <div className={col}>
        {head("O‘quv jadvali", timetable?.academic_semester || "Semestr jadvali", "timetable", "Jadvalni ochish")}
        {timetable && timetable.total_slots > 0 ? (
          <>
            <p className="font-display text-3xl font-bold tabular-nums"><CountUp value={timetable.groups.length} /> <span className="text-base font-semibold fb-muted">guruh</span></p>
            <div className="mt-auto flex flex-wrap items-center gap-4 text-xs fb-muted">
              <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" /> {timetable.total_slots} dars</span>
              <span className="inline-flex items-center gap-1.5"><GraduationCap className="h-3.5 w-3.5" /> {timetable.students_synced_count} talaba</span>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold">Jadval hali kiritilmagan</p>
            <p className="mt-auto text-xs fb-muted">Talabalar bo‘sh vaqti jadvaldan hisoblanadi.</p>
          </>
        )}
      </div>
    </section>
  );
}

/** Bento overview for university staff (design prototype applied to the academic portal). */
export default function UniversityOverview(props: UniversityOverviewProps) {
  const today = props.today ?? new Date();
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-[var(--fb-ink-muted)]">Salom, {firstName(props.name, "hurmatli xodim")}</p>
          <h1 className="fb-display mt-1">Akademik panel</h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--fb-ink-secondary)]">
            {[props.institutionName, props.institutionRegion].filter(Boolean).join(" · ") || "Talabalar amaliyoti, kundaliklar va o‘quv jadvali"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="fb-capsule inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" /> {uzDate(today)}
          </span>
          <span className="fb-nav-active rounded-full px-3.5 py-2 text-xs">{props.isCoordinator ? "Koordinator" : "O‘qituvchi"}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1fr)]">
        <QueueFlow {...props} today={today} />
        <CoverageCard {...props} />
        <NextReviewCard {...props} today={today} />
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,2.6fr)]">
        <PeopleCard {...props} />
        <div className="flex min-w-0 flex-col gap-5">
          <CountsStrip {...props} />
          <InkPanel {...props} />
        </div>
      </div>
    </div>
  );
}
