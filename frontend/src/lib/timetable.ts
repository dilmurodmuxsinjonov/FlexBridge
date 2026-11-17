import { errorText } from "./errorText";

export interface ClassSlot {
  weekday: number; // 1 = Dushanba .. 7 = Yakshanba
  weekday_name: string;
  para_number: number;
  start_time: string;
  end_time: string;
  start_minute: number;
  end_minute: number;
  subject_name: string;
  lesson_type: string;
  room: string;
  teacher_name: string;
}

export interface FreeDay {
  weekday: number;
  weekday_name: string;
  class_count: number;
  free_intervals: Array<{ start_minute: number; end_minute: number; start_time: string; end_time: string; duration_minutes: number }>;
}

export type MyTimetableStatus = "OK" | "NO_VERIFIED_ENROLLMENT" | "TIMETABLE_NOT_PUBLISHED";

export interface MyTimetable {
  status: MyTimetableStatus;
  institution_name: string | null;
  program: string | null;
  group_code: string | null;
  matched_by: "PROGRAM" | "DEFAULT" | null;
  academic_semester: string | null;
  updated_at: string | null;
  commute_buffer_minutes?: number;
  slots: ClassSlot[];
  free_windows: FreeDay[];
}

export async function fetchMyTimetable(): Promise<MyTimetable> {
  const res = await fetch("/api/bff/candidate/timetable", { headers: { Accept: "application/json" }, cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errorText(data, "TIMETABLE_FETCH_FAILED"));
  return {
    status: data.status ?? "TIMETABLE_NOT_PUBLISHED",
    institution_name: data.institution_name ?? null,
    program: data.program ?? null,
    group_code: data.group_code ?? null,
    matched_by: data.matched_by ?? null,
    academic_semester: data.academic_semester ?? null,
    updated_at: data.updated_at ?? null,
    commute_buffer_minutes: data.commute_buffer_minutes,
    slots: Array.isArray(data.slots) ? data.slots : [],
    free_windows: Array.isArray(data.free_windows) ? data.free_windows : [],
  };
}

export const LESSON_LABEL: Record<string, string> = {
  "MA'RUZA": "Ma’ruza",
  AMALIYOT: "Amaliy",
  LABORATORIYA: "Laboratoriya",
  SEMINAR: "Seminar",
};

export const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

const toMinutes = (t: string) => {
  const m = /^(\d{1,2}):(\d{2})$/.exec(t.trim());
  return m ? Number(m[1]) * 60 + Number(m[2]) : NaN;
};

/** Classes of one ISO weekday, in time order. */
export function classesOn(slots: ClassSlot[], weekday: number): ClassSlot[] {
  return slots.filter((s) => s.weekday === weekday).sort((a, b) => a.start_minute - b.start_minute);
}

/** The class in progress at `now`, or the next one later today. */
export function currentOrNext(slots: ClassSlot[], now: Date): { slot: ClassSlot; inProgress: boolean } | null {
  const weekday = now.getDay() === 0 ? 7 : now.getDay();
  const minute = now.getHours() * 60 + now.getMinutes();
  for (const s of classesOn(slots, weekday)) {
    if (minute < s.end_minute) return { slot: s, inProgress: minute >= s.start_minute };
  }
  return null;
}

/**
 * Classes that overlap a work interval given as "HH:MM" strings (Labour Code
 * art. 118: practice hours must not clash with lessons). Invalid input -> [].
 */
export function workClashes(slots: ClassSlot[], weekday: number, start: string, end: string): ClassSlot[] {
  const a = toMinutes(start);
  const b = toMinutes(end);
  if (!Number.isFinite(a) || !Number.isFinite(b) || a >= b) return [];
  return classesOn(slots, weekday).filter((s) => s.start_minute < b && a < s.end_minute);
}
