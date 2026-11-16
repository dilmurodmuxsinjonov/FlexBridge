"use client";

import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { DailyLogItem } from "@/lib/api";
import { addMonths, monthGrid, monthTitle, STATUS_LABEL } from "@/lib/diary";

const HEAD = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

export interface DiaryCalendarProps {
  month: string; // "YYYY-MM"
  onMonthChange: (month: string) => void;
  logs: DailyLogItem[];
  selected: string;
  onSelect: (iso: string) => void;
  minDate: string;
  maxDate: string;
  today: string;
  /** ISO weekdays that have classes (shown as a small mark). */
  classDays?: Set<number>;
}

function cellClass(status: DailyLogItem["status"] | undefined): string {
  switch (status) {
    case "REVIEWED":
      return "bg-[var(--fb-pill-active-bg)] text-[var(--fb-pill-active-fg)]";
    case "SUBMITTED":
      return "ring-2 ring-inset ring-[var(--fb-ink)] text-[var(--fb-ink)] font-semibold";
    case "NEEDS_REVISION":
      return "bg-[var(--fb-accent)] text-white";
    case "DRAFT":
      return "border border-dashed border-[var(--fb-ink-muted)] text-[var(--fb-ink)]";
    default:
      return "text-[var(--fb-ink-secondary)] hover:bg-[var(--fb-well-deep)]";
  }
}

/** Month view of the diary: every day shows its entry status at a glance. */
export default function DiaryCalendar({ month, onMonthChange, logs, selected, onSelect, minDate, maxDate, today, classDays }: DiaryCalendarProps) {
  const byDate = new Map(logs.map((l) => [l.local_date, l]));
  const canPrev = addMonths(month, -1) >= minDate.slice(0, 7);
  const canNext = addMonths(month, 1) <= maxDate.slice(0, 7);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <button type="button" onClick={() => onMonthChange(addMonths(month, -1))} disabled={!canPrev} className="fb-icon-btn fb-icon-btn-light h-8 w-8 disabled:opacity-30" aria-label="Oldingi oy">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <p className="text-sm font-semibold text-[var(--fb-ink)]" aria-live="polite">{monthTitle(month)}</p>
        <button type="button" onClick={() => onMonthChange(addMonths(month, 1))} disabled={!canNext} className="fb-icon-btn fb-icon-btn-light h-8 w-8 disabled:opacity-30" aria-label="Keyingi oy">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center" aria-label={`${monthTitle(month)} kundaligi`} role="group">
        {HEAD.map((h) => (
          <span key={h} className="pb-1 text-[11px] font-medium text-[var(--fb-ink-muted)]" aria-hidden="true">{h}</span>
        ))}
        {monthGrid(month).map((iso, i) => {
          if (!iso) return <span key={`pad-${i}`} aria-hidden="true" />;
          const log = byDate.get(iso);
          const disabled = iso < minDate || iso > maxDate;
          const isSelected = iso === selected;
          const weekday = ((i % 7) + 1);
          const label = `${iso}${log ? `, ${STATUS_LABEL[log.status]}` : ""}`;
          return (
            <button
              key={iso}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(iso)}
              aria-pressed={isSelected}
              aria-label={label}
              title={label}
              className={`relative mx-auto flex h-9 w-9 items-center justify-center rounded-full text-xs tabular-nums transition-colors disabled:cursor-not-allowed disabled:opacity-25 ${cellClass(log?.status)} ${
                isSelected ? "outline outline-2 outline-offset-2 outline-[var(--fb-accent)]" : ""
              } ${iso === today ? "font-bold" : ""}`}
            >
              {Number(iso.slice(8))}
              {classDays?.has(weekday) && !disabled && (
                <span aria-hidden="true" className="absolute bottom-0.5 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-[var(--fb-ink-muted)]" />
              )}
            </button>
          );
        })}
      </div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1.5 text-[11px] text-[var(--fb-ink-muted)]">
        <li className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-[var(--fb-pill-active-bg)]" />Tasdiqlangan</li>
        <li className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full ring-2 ring-inset ring-[var(--fb-ink)]" />Tekshiruvda</li>
        <li className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full bg-[var(--fb-accent)]" />Izoh bor</li>
        <li className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border border-dashed border-[var(--fb-ink-muted)]" />Qoralama</li>
        {classDays && <li className="inline-flex items-center gap-1.5"><span className="h-1 w-1 rounded-full bg-[var(--fb-ink-muted)]" />Dars bor</li>}
      </ul>
    </div>
  );
}
