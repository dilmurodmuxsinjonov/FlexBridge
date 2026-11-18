"use client";

import Link from "next/link";
import {
  ArrowRight,
  BriefcaseBusiness,
  Building2,
  Clock3,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import type { Opportunity } from "@/lib/api";
import { enumLabel } from "@/lib/labels";

const MODE_LABELS: Record<string, string> = {
  ONSITE: "Ish joyida",
  HYBRID: "Gibrid",
  REMOTE: "Masofadan",
};

export function paymentLabel(job: Opportunity): string {
  if (!job.is_paid) return "To‘lovsiz (amaliyot)";
  const format = (value: number) => value.toLocaleString("uz-UZ");
  if (job.salary_min !== null && job.salary_max !== null) {
    return `${format(job.salary_min)}–${format(job.salary_max)} ${job.currency}`;
  }
  if (job.salary_min !== null) return `${format(job.salary_min)} ${job.currency} dan`;
  if (job.salary_max !== null) return `${format(job.salary_max)} ${job.currency} gacha`;
  return "Kelishuv asosida";
}

export default function VacancyCard({
  job,
  compact = false,
}: {
  job: Opportunity;
  compact?: boolean;
}) {
  const place = job.region || job.organization_region;
  const mode = job.work_mode ? MODE_LABELS[job.work_mode] || enumLabel(job.work_mode) : null;
  const posted = job.published_at ? new Date(job.published_at) : null;
  const postedLabel =
    posted && !Number.isNaN(posted.getTime()) ? posted.toLocaleDateString("uz-UZ") : null;

  return (
    <article className="fb-panel skeuo-card skeuo-card-interactive flex h-full flex-col justify-between gap-4 p-5 sm:p-6">
      <div className="flex flex-col gap-3.5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 gap-3.5">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl skeuo-well text-[#c94f1d] dark:text-[#f47a3d]">
            <Building2 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="truncate text-xs font-semibold text-[var(--fb-ink)]">
                {job.organization_name}
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-600/25 bg-emerald-600/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:text-emerald-300">
                <ShieldCheck className="h-3 w-3 shrink-0" aria-hidden="true" />
                <span>Tasdiqlangan</span>
              </span>
            </div>
            <h3 className="font-display text-base font-bold leading-snug text-[var(--fb-ink)] transition-colors hover:text-[#c94f1d] dark:hover:text-[#f47a3d]">
              <Link href={`/ishlar/${job.id}`} prefetch={false} className="break-words">
                {job.title}
              </Link>
            </h3>
            <div className="mt-2 flex flex-wrap gap-x-3.5 gap-y-1 text-xs text-[var(--fb-ink-muted)]">
              {place && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>{place}</span>
                </span>
              )}
              {mode && (
                <span className="inline-flex items-center gap-1">
                  <BriefcaseBusiness className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>{mode}</span>
                </span>
              )}
              {postedLabel && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>{postedLabel}</span>
                </span>
              )}
            </div>
          </div>
        </div>
        <span className="shrink-0 self-start rounded-full skeuo-badge-recessed px-2.5 py-1 text-[11px] font-semibold text-[var(--fb-ink)]">
          {enumLabel(job.kind)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 rounded-2xl skeuo-well px-3.5 py-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium text-[var(--fb-ink-muted)]">To‘lov sharti</p>
          <p className="mt-0.5 truncate text-xs sm:text-sm font-bold text-[#c94f1d] dark:text-[#f47a3d] tabular-nums">
            {paymentLabel(job)}
          </p>
        </div>
        <div className="min-w-0 border-l border-[var(--fb-border)] pl-3">
          <p className="text-[11px] font-medium text-[var(--fb-ink-muted)]">Bo‘sh o‘rin</p>
          <p className="mt-0.5 text-xs sm:text-sm font-bold text-[var(--fb-ink)] tabular-nums">
            {job.vacancies_available} ta kvota
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        {!compact && job.description ? (
          <details className="group min-w-0 flex-1 text-xs text-[var(--fb-ink-secondary)]">
            <summary className="inline-flex cursor-pointer list-none items-center gap-1 font-semibold text-[var(--fb-ink)] hover:text-[#c94f1d] dark:hover:text-[#f47a3d]">
              <span>Tavsifni ko‘rish</span>
              <ArrowRight
                className="h-3.5 w-3.5 transition-transform group-open:rotate-90"
                aria-hidden="true"
              />
            </summary>
            <p className="mt-2 whitespace-pre-wrap leading-relaxed text-[var(--fb-ink-muted)]">
              {job.description}
            </p>
          </details>
        ) : (
          <p className="min-w-0 flex-1 truncate text-xs text-[var(--fb-ink-muted)]">
            {job.schedule_policy || "Dars jadvaliga moslashuvchan tartib"}
          </p>
        )}

        <Link
          href={`/ishlar/${job.id}`}
          prefetch={false}
          className="skeuo-btn-obsidian group shrink-0 rounded-full px-4 py-2 text-xs"
        >
          <span>Batafsil</span>
          <ArrowRight
            className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </Link>
      </div>
    </article>
  );
}
