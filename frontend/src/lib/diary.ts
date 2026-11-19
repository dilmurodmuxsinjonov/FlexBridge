import type { DailyLogItem } from "./api";

type RawReview = { decision?: string; comment?: string | null; decided_at?: string };
type RawTask = { id?: string; title?: string; result_text?: string; minutes?: number; start_minute?: number | null; end_minute?: number | null; evidence_count?: number };
type RawRevision = {
  id?: string;
  revision?: number;
  day_type?: string;
  summary?: string;
  total_minutes?: number;
  status?: string;
  submitted_at?: string | null;
  tasks?: RawTask[];
  workplace_reviews?: RawReview[];
  academic_reviews?: RawReview[];
};
export type RawLog = RawRevision & { id: string; placement_id: string; local_date: string; current_revision?: RawRevision | null };

const NEGATIVE = new Set(["REJECTED", "CHANGES_REQUESTED", "NEEDS_REVISION"]);
const POSITIVE = new Set(["APPROVED", "REVIEWED"]);

export interface DiaryReview {
  by: "MENTOR" | "OTM";
  decision: string;
  comment?: string | null;
  decided_at: string;
}

/** All reviews of a log, newest first, labelled by who gave them. */
export function reviewsOf(log: DailyLogItem): DiaryReview[] {
  const w = (log.workplace_reviews || []).map((r) => ({ by: "MENTOR" as const, ...r }));
  const a = (log.academic_reviews || []).map((r) => ({ by: "OTM" as const, ...r }));
  return [...w, ...a].sort((x, y) => (y.decided_at || "").localeCompare(x.decided_at || ""));
}

/**
 * The backend nests the current revision (`current_revision`) and names task text
 * `result_text`; review outcomes live in separate review lists. This flattens a log
 * to the shape the diary UI uses and derives the displayed status:
 * newest review negative -> NEEDS_REVISION, any approval otherwise -> REVIEWED.
 */
export function normalizeLog(raw: RawLog): DailyLogItem {
  const rev: RawRevision = raw.current_revision ?? raw;
  const base: DailyLogItem = {
    id: raw.id,
    placement_id: raw.placement_id,
    local_date: raw.local_date,
    current_revision_id: rev.id ?? "",
    revision: rev.revision ?? 1,
    day_type: rev.day_type === "ABSENT" ? "ABSENT" : "WORKED",
    summary: rev.summary ?? "",
    total_minutes: rev.total_minutes ?? 0,
    status: (rev.status as DailyLogItem["status"]) ?? "DRAFT",
    submitted_at: rev.submitted_at ?? null,
    tasks: (rev.tasks || []).map((t) => ({
      id: t.id,
      title: t.title ?? t.result_text ?? "",
      minutes: t.minutes ?? 0,
      ...(typeof t.evidence_count === "number" ? { evidence_count: t.evidence_count } : {}),
    })),
    workplace_reviews: (rev.workplace_reviews || []).map((r) => ({ decision: r.decision ?? "", comment: r.comment ?? undefined, decided_at: r.decided_at ?? "" })),
    academic_reviews: (rev.academic_reviews || []).map((r) => ({ decision: r.decision ?? "", comment: r.comment ?? undefined, decided_at: r.decided_at ?? "" })),
  };
  if (base.status === "SUBMITTED") {
    const latest = reviewsOf(base)[0];
    if (latest && NEGATIVE.has(latest.decision)) base.status = "NEEDS_REVISION";
    else if (reviewsOf(base).some((r) => POSITIVE.has(r.decision))) base.status = "REVIEWED";
  }
  return base;
}

/** Local calendar date "YYYY-MM-DD" (not UTC: after midnight in Tashkent UTC is still yesterday). */
export function localISODate(d = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Monday-first month grid (6 rows max) for `month` ("YYYY-MM"); null = padding cell. */
export function monthGrid(month: string): Array<string | null> {
  const [y, m] = month.split("-").map(Number);
  const first = new Date(y, m - 1, 1);
  const days = new Date(y, m, 0).getDate();
  const lead = (first.getDay() + 6) % 7;
  const cells: Array<string | null> = Array.from({ length: lead }, () => null);
  for (let d = 1; d <= days; d++) cells.push(`${month}-${String(d).padStart(2, "0")}`);
  while (cells.length % 7) cells.push(null);
  return cells;
}

/** ISO weekday (1 Mon..7 Sun) of a "YYYY-MM-DD" date in local time. */
export function weekdayOf(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  const day = new Date(y, m - 1, d).getDay();
  return day === 0 ? 7 : day;
}

export const DECISION_LABEL: Record<string, string> = {
  APPROVED: "Tasdiqladi",
  CHANGES_REQUESTED: "Tuzatish so‘radi",
  REJECTED: "Rad etdi",
  REVIEWED: "Ko‘rib chiqdi",
  NEEDS_REVISION: "Qayta ishlashni so‘radi",
};

export const STATUS_LABEL: Record<DailyLogItem["status"], string> = {
  DRAFT: "Qoralama",
  SUBMITTED: "Tekshiruvda",
  REVIEWED: "Tasdiqlangan",
  NEEDS_REVISION: "Izoh bor",
};

const UZ_MONTHS = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];
const UZ_WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];

/** "Noyabr 2026" for "2026-11". */
export function monthTitle(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${UZ_MONTHS[m - 1]} ${y}`;
}

/** "16-noyabr, Dushanba" for "2026-11-16". */
export function longDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${d}-${UZ_MONTHS[m - 1].toLowerCase()}, ${UZ_WEEKDAYS[weekdayOf(iso) - 1]}`;
}

/** Shift "YYYY-MM" by n months. */
export function addMonths(month: string, n: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + n, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
