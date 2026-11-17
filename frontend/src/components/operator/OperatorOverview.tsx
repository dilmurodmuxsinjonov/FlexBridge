"use client";

import React from "react";
import {
  ArrowUpRight,
  CalendarDays,
  CreditCard,
  FileCheck2,
  FolderSearch,
  KeyRound,
  Scale,
  ShieldAlert,
  Sliders,
  Users,
} from "lucide-react";
import type { OperatorAuditEventItem, OperatorSupportTicketItem, OperatorVerificationCaseItem } from "@/lib/api";
import { enumLabel } from "@/lib/labels";
import { firstName, uzDate } from "@/lib/person";
import CountUp from "@/components/motion/CountUp";
import type { GovernanceSection } from "./GovernanceOpsPanel";

export type OperatorTab =
  | "STAFF_ROLES"
  | "DIRECTORY"
  | "FEATURE_FLAGS"
  | "GOVERNANCE"
  | "AUDIT"
  | "VERIFICATION"
  | "MODERATION"
  | "BREAK_GLASS"
  | "SUPPORT_OPS"
  | "FINANCE";

export interface OperatorOverviewProps {
  name?: string | null;
  roles: string[];
  visible: OperatorTab[];
  cases: OperatorVerificationCaseItem[];
  tickets: OperatorSupportTicketItem[];
  auditEvents: OperatorAuditEventItem[];
  discrepancies: number | null;
  /** Draft vacancies waiting for a moderator (null when the role cannot moderate). */
  moderationCount?: number | null;
  activeStaffGrantsCount?: number | null;
  pendingPrivacyCount?: number | null;
  pendingRecoveryCount?: number | null;
  enabledR1FlagsCount?: number | null;
  appealsCount?: number | null;
  onOpen: (tab: OperatorTab) => void;
  onOpenGovernance?: (section: GovernanceSection) => void;
  /** Injected for tests; defaults to now. */
  today?: Date;
}

const OPEN_CASE = new Set(["OPEN", "NEW", "PENDING", "IN_REVIEW", "NEEDS_INFO", "SUBMITTED"]);
const CLOSED_TICKET = new Set(["RESOLVED", "CLOSED"]);
const URGENT = new Set(["URGENT", "CRITICAL", "HIGH"]);

/** "ORG_VERIFICATION_DECIDED" -> "Org verification decided" (operators read these; no raw codes). */
const actionText = (a: string) => enumLabel(a);

export function attentionItems(
  p: Pick<
    OperatorOverviewProps,
    | "cases"
    | "tickets"
    | "discrepancies"
    | "visible"
    | "moderationCount"
    | "pendingRecoveryCount"
    | "pendingPrivacyCount"
    | "appealsCount"
  >
) {
  const items: Array<{ key: string; text: string; tab: OperatorTab; count: number; governanceSection?: GovernanceSection }> = [];
  const urgent = p.tickets.filter((t) => !CLOSED_TICKET.has(t.status) && URGENT.has(t.priority)).length;
  const overdueCases = p.cases.filter((c) => OPEN_CASE.has(c.status || "") && c.due_at && new Date(c.due_at) < new Date()).length;
  if (p.visible.includes("SUPPORT_OPS") && urgent) items.push({ key: "urgent", text: "muhim murojaat (shoshilinch / yuqori)", tab: "SUPPORT_OPS", count: urgent });
  if (p.visible.includes("VERIFICATION") && overdueCases) items.push({ key: "overdue", text: "tekshiruv muddati o‘tgan", tab: "VERIFICATION", count: overdueCases });
  if (p.visible.includes("MODERATION") && p.moderationCount) items.push({ key: "moderation", text: "e’lon moderatsiyani kutmoqda", tab: "MODERATION", count: p.moderationCount });
  if (p.visible.includes("GOVERNANCE") && p.pendingRecoveryCount) {
    items.push({
      key: "recovery",
      text: "parol tiklash so‘rovi tasdiq kutmoqda",
      tab: "GOVERNANCE",
      count: p.pendingRecoveryCount,
      governanceSection: "RECOVERY",
    });
  }
  if (p.visible.includes("GOVERNANCE") && p.pendingPrivacyCount) {
    items.push({
      key: "privacy",
      text: "ochiq maxfiylik (GDPR) so‘rovi",
      tab: "GOVERNANCE",
      count: p.pendingPrivacyCount,
      governanceSection: "PRIVACY",
    });
  }
  if (p.visible.includes("GOVERNANCE") && p.appealsCount) {
    items.push({
      key: "appeals",
      text: "apellyatsiya ko‘rib chiqilishini kutmoqda",
      tab: "GOVERNANCE",
      count: p.appealsCount,
      governanceSection: "APPEALS",
    });
  }
  if (p.visible.includes("FINANCE") && p.discrepancies) items.push({ key: "recon", text: "to‘lovda nomuvofiqlik", tab: "FINANCE", count: p.discrepancies });
  return items;
}

function CasesCard({ cases, onOpen }: OperatorOverviewProps) {
  const open = cases.filter((c) => OPEN_CASE.has(c.status || "")).length;
  const done = cases.length - open;
  const pct = cases.length ? Math.round((done / cases.length) * 100) : 0;
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="op-cases">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="op-cases" className="text-base font-semibold text-[var(--fb-ink)]">Tekshiruv navbati</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">Tashkilot va universitet arizalari</p>
        </div>
        <button type="button" onClick={() => onOpen("VERIFICATION")} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Tekshiruv navbatini ochish">
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
      <p className="font-display text-5xl font-bold tabular-nums text-[var(--fb-ink)]"><CountUp value={open} /></p>
      <p className="-mt-3 text-xs text-[var(--fb-ink-muted)]">ko‘rib chiqilishi kerak</p>
      <div className="fb-progress" role="img" aria-label={`${cases.length} tadan ${done} tasi hal qilingan`}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <ul className="flex flex-col gap-1.5">
        {cases
          .filter((c) => OPEN_CASE.has(c.status || ""))
          .slice(0, 3)
          .map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-2 text-xs">
              <span className="min-w-0 truncate font-semibold text-[var(--fb-ink)]">{c.organization_name || c.institution_name || "Ariza"}</span>
              <span className="shrink-0 text-[var(--fb-ink-muted)]">{enumLabel(c.status)}</span>
            </li>
          ))}
      </ul>
    </section>
  );
}

function TicketsCard({ tickets, onOpen }: OperatorOverviewProps) {
  const open = tickets.filter((t) => !CLOSED_TICKET.has(t.status));
  const groups = ["URGENT", "HIGH", "MEDIUM", "LOW"].map((p) => ({ p, n: open.filter((t) => t.priority === p).length }));
  const top = Math.max(1, ...groups.map((g) => g.n));
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="op-tickets">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="op-tickets" className="text-base font-semibold text-[var(--fb-ink)]">Murojaatlar</h2>
          <p className="text-xs text-[var(--fb-ink-muted)]">Ochiq murojaatlar muhimligi bo‘yicha</p>
        </div>
        <button type="button" onClick={() => onOpen("SUPPORT_OPS")} className="fb-icon-btn fb-icon-btn-light h-9 w-9" aria-label="Murojaatlarni ochish">
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
      <ol className="flex flex-col gap-2.5">
        {groups.map(({ p, n }) => (
          <li key={p} className="flex items-center gap-3">
            <span className="w-24 shrink-0 text-xs text-[var(--fb-ink-secondary)]">{enumLabel(p)}</span>
            <span className="relative h-6 flex-1 rounded-full bg-[color-mix(in_srgb,var(--fb-well-deep)_50%,transparent)]">
              {n > 0 && <span className={`fb-bar absolute inset-y-0 left-0 ${p === "URGENT" ? "fb-bar-today" : ""}`} style={{ width: `${Math.max(10, (n / top) * 100)}%` }} />}
            </span>
            <span className="w-8 shrink-0 text-right text-sm font-bold tabular-nums text-[var(--fb-ink)]">{n}</span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-[var(--fb-ink-secondary)]">{open.length ? `Jami ${open.length} ta ochiq` : "Ochiq murojaat yo‘q"}</p>
    </section>
  );
}

function AttentionCard(props: OperatorOverviewProps) {
  const items = attentionItems(props);
  return (
    <section data-skeuo-dark="true" className="fb-ink-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="op-attention">
      <div className="flex items-center justify-between">
        <h2 id="op-attention" className="text-sm font-semibold fb-muted">Diqqat talab qiladi</h2>
        <ShieldAlert className="h-4 w-4 fb-muted" aria-hidden="true" />
      </div>
      {items.length === 0 ? (
        <div className="flex flex-1 flex-col justify-center gap-2">
          <p className="text-lg font-semibold">Hammasi joyida</p>
          <p className="text-xs fb-muted">Shoshilinch murojaat, muddati o‘tgan tekshiruv yoki to‘lov nomuvofiqligi yo‘q.</p>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((i) => (
            <li key={i.key}>
              <button
                type="button"
                onClick={() => {
                  if (i.governanceSection && props.onOpenGovernance) {
                    props.onOpenGovernance(i.governanceSection);
                  } else {
                    props.onOpen(i.tab);
                  }
                }}
                className="flex w-full items-center justify-between gap-3 rounded-2xl bg-white/5 px-4 py-3 text-left hover:bg-white/10"
              >
                <span className="text-sm">
                  <span className="font-display text-2xl font-bold tabular-nums">{i.count}</span> <span className="fb-muted">{i.text}</span>
                </span>
                <ArrowUpRight className="h-4 w-4 shrink-0" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AuditList({ auditEvents, onOpen }: OperatorOverviewProps) {
  return (
    <section className="fb-panel skeuo-card flex flex-col gap-4 p-5 sm:p-6" aria-labelledby="op-audit">
      <div className="flex items-center justify-between">
        <h2 id="op-audit" className="text-base font-semibold text-[var(--fb-ink)]">So‘nggi hodisalar</h2>
        <button type="button" onClick={() => onOpen("AUDIT")} className="fb-icon-btn h-9 w-9" aria-label="Audit jurnalini ochish">
          <FileCheck2 className="h-4 w-4" />
        </button>
      </div>
      {auditEvents.length === 0 ? (
        <p className="rounded-[18px] skeuo-well px-4 py-6 text-center text-xs text-[var(--fb-ink-secondary)]">Hodisalar hali yuklanmagan.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {auditEvents.slice(0, 5).map((e) => (
            <li key={e.id} className="fb-file-row">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold text-[var(--fb-ink)]">{actionText(e.action)}</span>
                <span className="block truncate text-[11px] text-[var(--fb-ink-muted)]">
                  {enumLabel(e.object_type, "Tizim")} · {e.occurred_at ? new Date(e.occurred_at).toLocaleString("uz-UZ") : ""}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function InkPanel({ auditEvents, discrepancies, visible, onOpen }: OperatorOverviewProps) {
  const col = "flex min-w-0 flex-col gap-3 p-5 sm:p-6";
  const head = (title: string, sub: string, tab: OperatorTab, Icon: typeof FileCheck2) => (
    <div className="flex items-start justify-between gap-2">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="truncate text-xs fb-muted">{sub}</p>
      </div>
      <button type="button" onClick={() => onOpen(tab)} className="fb-muted hover:text-white" aria-label={`${title}ni ochish`}>
        <Icon className="h-4 w-4" />
      </button>
    </div>
  );
  const cols = [
    visible.includes("AUDIT") && (
      <div key="audit" className={col}>
        {head("Audit jurnali", "O‘zgartirib bo‘lmaydigan yozuvlar", "AUDIT", FileCheck2)}
        <p className="font-display text-3xl font-bold tabular-nums"><CountUp value={auditEvents.length} /></p>
        <p className="-mt-2 text-xs fb-muted">yuklangan hodisa</p>
      </div>
    ),
    visible.includes("FINANCE") && (
      <div key="fin" className={col}>
        {head("Moliya", "To‘lovlar solishtiruvi", "FINANCE", CreditCard)}
        <p className="font-display text-3xl font-bold tabular-nums">{discrepancies == null ? "—" : <CountUp value={discrepancies} />}</p>
        <p className="-mt-2 text-xs fb-muted">nomuvofiqlik</p>
      </div>
    ),
    visible.includes("BREAK_GLASS") && (
      <div key="bg" className={col}>
        {head("Favqulodda ruxsat", "Ikki kishi tasdig‘i bilan, vaqtinchalik", "BREAK_GLASS", ShieldAlert)}
        <p className="text-sm">Faqat hodisa paytida va sabab yozilgan holda ishlating.</p>
      </div>
    ),
  ].filter(Boolean);
  if (cols.length === 0) return null;
  return (
    <section
      data-skeuo-dark="true"
      className={`fb-ink-card grid grid-cols-1 divide-y divide-white/10 md:divide-x md:divide-y-0 ${cols.length === 3 ? "md:grid-cols-3" : cols.length === 2 ? "md:grid-cols-2" : ""}`}
      aria-label="Operator ko‘rsatkichlari"
    >
      {cols}
    </section>
  );
}

function SuperAdminQuickGrid(props: OperatorOverviewProps) {
  const { visible, onOpen, onOpenGovernance } = props;
  const cards = [
    visible.includes("STAFF_ROLES") && {
      key: "STAFF_ROLES" as OperatorTab,
      title: "Xodim rollari va matritsa",
      subtitle: "Kim qaysi rolni beradi, doimiy tayinlov",
      metric:
        props.activeStaffGrantsCount != null
          ? `${props.activeStaffGrantsCount} ta faol vakolat`
          : "Vakolatlar matritsasi",
      Icon: Users,
      onClick: () => onOpen("STAFF_ROLES"),
    },
    visible.includes("FEATURE_FLAGS") && {
      key: "FEATURE_FLAGS" as OperatorTab,
      title: "Funksional flaglar",
      subtitle: "R1 boshqaruvi va himoyalangan qulflar",
      metric:
        props.enabledR1FlagsCount != null
          ? `${props.enabledR1FlagsCount} ta R1 flag faol`
          : "Global flaglar holati",
      Icon: Sliders,
      onClick: () => onOpen("FEATURE_FLAGS"),
    },
    visible.includes("DIRECTORY") && {
      key: "DIRECTORY" as OperatorTab,
      title: "Katalog va reyestr",
      subtitle: "Foydalanuvchilar, korxonalar va OTM",
      metric: "Yagona tezkor qidiruv",
      Icon: FolderSearch,
      onClick: () => onOpen("DIRECTORY"),
    },
    visible.includes("GOVERNANCE") && {
      key: "GOVERNANCE" as OperatorTab,
      title: "Komplayens va tiklash",
      subtitle: "GDPR, parol tiklash, apellyatsiya, vorislik",
      metric:
        props.pendingRecoveryCount || props.pendingPrivacyCount
          ? `${(props.pendingRecoveryCount ?? 0) + (props.pendingPrivacyCount ?? 0)} ta kutayotgan ariza`
          : "Boshqaruv navbatlari",
      Icon: Scale,
      onClick: () => (onOpenGovernance ? onOpenGovernance("PRIVACY") : onOpen("GOVERNANCE")),
    },
  ].filter((c): c is Exclude<typeof c, false> => Boolean(c));

  if (cards.length === 0) return null;

  return (
    <section aria-label="Boshqaruv tezkor bo‘limlari" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ key, title, subtitle, metric, Icon, onClick }) => (
        <button
          key={key}
          type="button"
          onClick={onClick}
          className="fb-panel skeuo-card skeuo-card-interactive flex flex-col justify-between gap-3 p-4 text-left"
        >
          <div className="flex items-start justify-between gap-2">
            <span className="fb-avatar h-9 w-9 shrink-0" aria-hidden="true">
              <Icon className="h-4 w-4" />
            </span>
            <ArrowUpRight className="h-4 w-4 text-[var(--fb-ink-muted)]" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-[var(--fb-ink)]">{title}</h2>
            <p className="mt-0.5 text-xs text-[var(--fb-ink-muted)]">{subtitle}</p>
          </div>
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--fb-ink-secondary)]">
            {key === "GOVERNANCE" && (props.pendingRecoveryCount ?? 0) > 0 && (
              <KeyRound className="h-3.5 w-3.5 text-[var(--fb-accent)]" aria-hidden="true" />
            )}
            <span>{metric}</span>
          </p>
        </button>
      ))}
    </section>
  );
}

/** Bento overview for platform operators (only the modules their role may open). */
export default function OperatorOverview(props: OperatorOverviewProps) {
  const today = props.today ?? new Date();
  const v = props.visible;
  const roleLabel = props.roles.length ? props.roles.map((r) => enumLabel(r)).join(", ") : "Operator";
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-[var(--fb-ink-muted)]">Salom, {firstName(props.name, "hurmatli operator")}</p>
          <h1 className="fb-display mt-1">Operator paneli</h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--fb-ink-secondary)]">Xodim rollari, flaglar, tekshiruvlar, moliya va audit — bitta joyda</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="fb-capsule inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" /> {uzDate(today)}
          </span>
          <span className="fb-nav-active rounded-full px-3.5 py-2 text-xs">{roleLabel}</span>
        </div>
      </header>
      <SuperAdminQuickGrid {...props} />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        {v.includes("VERIFICATION") && <CasesCard {...props} />}
        {v.includes("SUPPORT_OPS") && <TicketsCard {...props} />}
        <AttentionCard {...props} />
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        {v.includes("AUDIT") ? <AuditList {...props} /> : <div className="hidden xl:block" />}
        <InkPanel {...props} />
      </div>
    </div>
  );
}
