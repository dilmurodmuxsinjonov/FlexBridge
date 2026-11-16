"use client";

import React from "react";
import { ArrowUpRight, Briefcase, CalendarDays, GraduationCap, MessageSquareText, Plus, Users } from "lucide-react";
import type { EmployerDashboardMetrics, ManagedOpportunityItem, MentorReviewQueueItem } from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import { firstName, uzDate } from "@/lib/person";

export type EmployerTab = "KANBAN" | "MENTOR_HUB" | "ORG_HUB" | "BILLING_HUB" | "SEARCH_HUB";

export interface EmployerOverviewProps {
  name?: string | null;
  orgName?: string | null;
  orgRegion?: string | null;
  roles: string[];
  metrics: EmployerDashboardMetrics["metrics"] | null;
  opportunities: ManagedOpportunityItem[];
  mentorQueue: MentorReviewQueueItem[] | null;
  onOpen: (tab: EmployerTab) => void;
  onOpenOpportunity: (opportunityId: string) => void;
  onCreate: () => void;
  /** Injected for tests; defaults to now. */
  today?: Date;
}

/** Hiring funnel stages; each later stage is a subset of the applications. */
export function funnelStages(m: EmployerDashboardMetrics["metrics"]) {
  const a = m.applications;
  return [
    { key: "total", label: "Arizalar", value: a.total },
    { key: "shortlisted", label: "Saralangan", value: a.shortlisted },
    { key: "interviewed", label: "Suhbatdan o‘tgan", value: a.interviewed },
    { key: "offered", label: "Taklif berilgan", value: a.offered },
    { key: "accepted", label: "Qabul qilgan", value: a.accepted },
  ];
}

const STATUS_ORDER = ["PUBLISHED", "APPROVED", "DRAFT", "PAUSED", "CLOSED"] as const;

/** Vacancy lifecycle in the words an employer needs: draft -> moderation -> approved -> published. */
const VACANCY_STATUS: Record<string, string> = {
  DRAFT: "Moderatsiyada",
  APPROVED: "Tasdiqlandi — e’lon qilish mumkin",
  REJECTED: "Moderator rad etdi",
};

function FunnelCard({ metrics, onOpen }: EmployerOverviewProps) {
  if (!metrics) return null;
  const stages = funnelStages(metrics);
  const top = Math.max(1, stages[0].value);
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="emp-funnel">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="emp-funnel" className="text-base font-semibold text-[var(--fb-ink)]">Nabor voronkasi</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">Barcha vakansiyalar bo‘yicha arizalar yo‘li</p>
        </div>
        <button type="button" onClick={() => onOpen("KANBAN")} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Nomzodlar kanbanini ochish">
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
      <ol className="flex flex-col gap-2.5">
        {stages.map((s, i) => (
          <li key={s.key} className="flex items-center gap-3">
            <span className="w-32 shrink-0 truncate text-xs text-[var(--fb-ink-secondary)]">{s.label}</span>
            <span className="relative h-7 flex-1 rounded-full bg-[color-mix(in_srgb,var(--fb-well-deep)_50%,transparent)]">
              <span
                className={`fb-bar absolute inset-y-0 left-0 ${i === stages.length - 1 ? "fb-bar-today" : ""}`}
                style={{ width: `${s.value ? Math.max(8, (s.value / top) * 100) : 0}%` }}
              />
            </span>
            <span className="w-10 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--fb-ink)]">{s.value}</span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-[var(--fb-ink-secondary)]">
        {stages[0].value
          ? `Arizalarning ${Math.round((stages[4].value / stages[0].value) * 100)}% qabul bilan yakunlangan · ${metrics.applications.pending} ta javob kutmoqda`
          : "Hali ariza kelmagan — vakansiya e’lon qiling."}
      </p>
    </section>
  );
}

function OpportunitiesCard({ metrics, onCreate }: EmployerOverviewProps) {
  if (!metrics) return null;
  const o = metrics.opportunities;
  const parts = [
    { key: "PUBLISHED", value: o.published, cls: "bg-[var(--fb-ink)]" },
    { key: "DRAFT", value: o.draft, cls: "bg-[color-mix(in_srgb,var(--fb-ink-muted)_60%,transparent)]" },
    { key: "PAUSED", value: o.paused, cls: "bg-[var(--fb-accent)]" },
    { key: "CLOSED", value: o.closed, cls: "bg-[var(--fb-well-deep)]" },
  ];
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="emp-opps">
      <div className="flex items-center justify-between">
        <h2 id="emp-opps" className="text-base font-semibold text-[var(--fb-ink)]">Vakansiyalar</h2>
        <button type="button" onClick={onCreate} className="fb-icon-btn h-9 w-9" aria-label="Yangi e’lon joylash">
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <p className="font-display text-5xl font-bold tracking-tight tabular-nums text-[var(--fb-ink)]">
        {o.published}
        <span className="ml-1 text-xl font-semibold text-[var(--fb-ink-muted)]">/ {o.total}</span>
      </p>
      <p className="-mt-3 text-xs text-[var(--fb-ink-muted)]">e’lon qilingan</p>
      <div className="flex h-2 gap-1" aria-hidden="true">
        {o.total ? parts.filter((p) => p.value).map((p) => <span key={p.key} className={`rounded-full ${p.cls}`} style={{ flex: p.value }} />) : <span className="flex-1 rounded-full bg-[var(--fb-well-deep)]" />}
      </div>
      <ul className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        {parts.map((p) => (
          <li key={p.key} className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-[var(--fb-ink-secondary)]"><span className={`h-2.5 w-2.5 rounded-full ${p.cls}`} />{enumLabel(p.key)}</span>
            <span className="font-semibold tabular-nums">{p.value}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TopOpportunityCard({ opportunities, onOpenOpportunity, onCreate }: EmployerOverviewProps) {
  const top = [...opportunities].filter((o) => o.status === "PUBLISHED").sort((a, b) => b.applications_count - a.applications_count)[0];
  return (
    <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="emp-top">
      <div className="flex items-center justify-between">
        <h2 id="emp-top" className="text-sm font-semibold fb-muted">Eng faol vakansiya</h2>
        <Briefcase className="h-4 w-4 fb-muted" aria-hidden="true" />
      </div>
      {top ? (
        <>
          <div>
            <p className="font-display text-2xl font-bold leading-tight">{top.title}</p>
            <p className="mt-1 text-xs fb-muted">{[enumLabel(top.kind), top.region, top.work_mode && enumLabel(top.work_mode)].filter(Boolean).join(" · ")}</p>
          </div>
          <p className="text-sm"><span className="font-display text-3xl font-bold tabular-nums">{top.applications_count}</span> <span className="fb-muted">ariza</span></p>
          {top.capacity > 0 && (
            <div>
              <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
                <span>Band o‘rinlar</span>
                <span className="tabular-nums">{top.occupied_count}/{top.capacity}</span>
              </div>
              <div className="fb-progress"><span style={{ width: `${Math.min(100, (top.occupied_count / top.capacity) * 100)}%` }} /></div>
            </div>
          )}
          <button type="button" onClick={() => onOpenOpportunity(top.id)} className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-full bg-white px-4 py-2.5 text-xs font-semibold text-[#0c0d10]">
            Arizalarni ko‘rish <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        </>
      ) : (
        <div className="flex flex-1 flex-col justify-center gap-3">
          <p className="text-lg font-semibold">Faol e’lon yo‘q</p>
          <p className="text-xs fb-muted">E’lon joylang — talabalar dars jadvaliga mos smenalarni shu yerda ko‘radi.</p>
          <button type="button" onClick={onCreate} className="inline-flex w-fit items-center gap-1.5 rounded-full bg-white px-4 py-2 text-xs font-semibold text-[#0c0d10]">
            <Plus className="h-3.5 w-3.5" /> Yangi e’lon
          </button>
        </div>
      )}
    </section>
  );
}

function OpportunityList({ opportunities, onOpenOpportunity, onCreate }: EmployerOverviewProps) {
  const order = (s: string) => (STATUS_ORDER as readonly string[]).indexOf(s) + 1 || 9;
  const rows = [...opportunities].sort((a, b) => order(a.status) - order(b.status) || b.applications_count - a.applications_count);
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="emp-list">
      <div className="flex items-center justify-between">
        <h2 id="emp-list" className="text-base font-semibold text-[var(--fb-ink)]">E’lonlarim</h2>
        <button type="button" onClick={onCreate} className="fb-icon-btn h-9 w-9" aria-label="Yangi e’lon joylash">
          <Plus className="h-4 w-4" />
        </button>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-[18px] skeuo-well px-4 py-6 text-center text-xs text-[var(--fb-ink-secondary)]">Hali e’lon yo‘q.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.slice(0, 4).map((o) => (
            <li key={o.id}>
              <button type="button" onClick={() => onOpenOpportunity(o.id)} className="fb-file-row w-full text-left">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--fb-card-top)] shadow-sm">
                  <Briefcase className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold text-[var(--fb-ink)]">{o.title}</span>
                  <span className="block truncate text-[11px] text-[var(--fb-ink-muted)]">{VACANCY_STATUS[o.status] || enumLabel(o.status)} · {o.applications_count} ariza</span>
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

function CountsStrip({ metrics, mentorQueue }: EmployerOverviewProps) {
  if (!metrics) return null;
  const stats = [
    { label: "Javob kutayotgan ariza", value: metrics.applications.pending },
    { label: "Rejalashtirilgan suhbat", value: metrics.interviews.scheduled },
    { label: "Faol amaliyotchi", value: metrics.engagements.active },
    { label: "Mentor ko‘rigida", value: mentorQueue ? mentorQueue.length : "—" },
  ];
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:px-6 lg:flex-row lg:items-center" aria-labelledby="emp-today">
      <h2 id="emp-today" className="text-base font-semibold text-[var(--fb-ink)] lg:w-36 lg:shrink-0">Bugungi holat</h2>
      <dl className="grid flex-1 grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
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

function InkPanel({ metrics, mentorQueue, onOpen }: EmployerOverviewProps) {
  if (!metrics) return null;
  const i = metrics.interviews;
  const e = metrics.engagements;
  const escalated = (mentorQueue || []).filter((q) => q.is_escalated).length;
  const col = "flex min-w-0 flex-col gap-3 p-5 sm:p-6";
  const head = (title: string, sub: string, tab: EmployerTab, label: string) => (
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
    <section data-skeuo-dark="true" className="fb-ink-card grid grid-cols-1 divide-y divide-white/10 md:grid-cols-3 md:divide-x md:divide-y-0" aria-label="Korxona ko‘rsatkichlari">
      <div className={col}>
        {head("Suhbatlar", "Nomzodlar bilan uchrashuvlar", "KANBAN", "Kanbanni ochish")}
        <p className="font-display text-3xl font-bold tabular-nums">{i.total}</p>
        <div className="mt-auto">
          <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
            <span>O‘tkazilgan</span>
            <span className="tabular-nums">{i.completed}/{i.total}</span>
          </div>
          <div className="fb-progress"><span style={{ width: `${i.total ? (i.completed / i.total) * 100 : 0}%` }} /></div>
        </div>
        <div className="flex flex-wrap gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" /> {i.scheduled} rejada</span>
          {i.no_show > 0 && <span>{i.no_show} kelmagan</span>}
        </div>
      </div>
      <div className={col}>
        {head("Amaliyot va dual ta’lim", "Ish o‘rinlaridagi talabalar", "MENTOR_HUB", "Mentorlik bo‘limini ochish")}
        <p className="font-display text-3xl font-bold tabular-nums">{e.active} <span className="text-base font-semibold fb-muted">faol</span></p>
        <div className="mt-auto">
          <div className="mb-1.5 flex justify-between text-[11px] fb-muted">
            <span>Yakunlangan</span>
            <span className="tabular-nums">{e.completed}/{e.total}</span>
          </div>
          <div className="fb-progress"><span style={{ width: `${e.total ? (e.completed / e.total) * 100 : 0}%` }} /></div>
        </div>
        <div className="flex flex-wrap gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><GraduationCap className="h-3.5 w-3.5" /> {e.pending_start} boshlanishi kutilmoqda</span>
        </div>
      </div>
      <div className={col}>
        {head("Mentorlik", "Talabalar kundaliklari", "MENTOR_HUB", "Kundaliklar navbatini ochish")}
        <p className="font-display text-3xl font-bold tabular-nums">{mentorQueue ? mentorQueue.length : "—"}</p>
        <p className="-mt-2 text-xs fb-muted">kundalik ko‘rik kutmoqda</p>
        <div className="mt-auto flex flex-wrap gap-4 text-xs fb-muted">
          <span className="inline-flex items-center gap-1.5"><MessageSquareText className="h-3.5 w-3.5" /> {escalated ? `${escalated} tasi muddati o‘tgan` : "Muddati o‘tgan yo‘q"}</span>
          <span className="inline-flex items-center gap-1.5"><Users className="h-3.5 w-3.5" /> {e.disputed ? `${e.disputed} nizo` : "Nizo yo‘q"}</span>
        </div>
      </div>
    </section>
  );
}

/** Bento overview for company staff (design prototype applied to the employer portal). */
export default function EmployerOverview(props: EmployerOverviewProps) {
  const today = props.today ?? new Date();
  const roleLabel = props.roles.length ? props.roles.map((r) => enumLabel(r)).join(", ") : "Xodim";
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-[var(--fb-ink-muted)]">Salom, {firstName(props.name, "hurmatli hamkor")}</p>
          <h1 className="fb-display mt-1">Korxona paneli</h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--fb-ink-secondary)]">
            {[props.orgName, props.orgRegion].filter(Boolean).join(" · ") || "Vakansiyalar, nomzodlar va amaliyotchilar"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="fb-capsule inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" /> {uzDate(today)}
          </span>
          <span className="fb-capsule rounded-full px-3.5 py-2 text-xs font-semibold">{roleLabel}</span>
          <button type="button" onClick={props.onCreate} className="inline-flex items-center gap-1.5 rounded-full skeuo-btn-obsidian px-4 py-2 text-xs font-semibold">
            <Plus className="h-3.5 w-3.5" /> Yangi e’lon
          </button>
        </div>
      </header>

      {props.metrics && (
        <>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <FunnelCard {...props} />
            <OpportunitiesCard {...props} />
            <TopOpportunityCard {...props} />
          </div>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,2.6fr)]">
            <OpportunityList {...props} />
            <div className="flex min-w-0 flex-col gap-5">
              <CountsStrip {...props} />
              <InkPanel {...props} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
