import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { addMonths, localISODate, longDate, monthGrid, normalizeLog, reviewsOf, weekdayOf } from "./diary";
import { classesOn, currentOrNext, workClashes, type ClassSlot, type MyTimetable } from "./timetable";
import DiaryCalendar from "@/components/diary/DiaryCalendar";
import StudentTimetable from "@/components/timetable/StudentTimetable";

// Shape returned by GET /api/v1/placements/{id}/logs (API-053).
const backendLog = (over: Record<string, unknown> = {}) => ({
  id: "log-1",
  placement_id: "pl-1",
  local_date: "2026-11-16",
  version: 2,
  current_revision: {
    id: "rev-2",
    revision: 2,
    day_type: "WORKED",
    summary: "API yozdim",
    total_minutes: 300,
    status: "SUBMITTED",
    submitted_at: "2026-11-16T15:00:00Z",
    tasks: [{ id: "t1", result_text: "Buyurtmalar API", minutes: 300 }],
    workplace_reviews: [],
    academic_reviews: [],
    ...over,
  },
});

describe("normalizeLog", () => {
  it("flattens the nested current revision and maps task text", () => {
    const log = normalizeLog(backendLog());
    expect(log).toMatchObject({ id: "log-1", local_date: "2026-11-16", status: "SUBMITTED", total_minutes: 300, summary: "API yozdim", current_revision_id: "rev-2" });
    expect(log.tasks).toEqual([{ id: "t1", title: "Buyurtmalar API", minutes: 300 }]);
  });

  it("derives the shown status from the newest review", () => {
    const approved = normalizeLog(backendLog({ workplace_reviews: [{ decision: "APPROVED", decided_at: "2026-11-17T09:00:00Z" }] }));
    expect(approved.status).toBe("REVIEWED");
    const returned = normalizeLog(
      backendLog({
        workplace_reviews: [{ decision: "APPROVED", decided_at: "2026-11-17T09:00:00Z" }],
        academic_reviews: [{ decision: "NEEDS_REVISION", comment: "Natijani aniqroq yozing", decided_at: "2026-11-18T09:00:00Z" }],
      })
    );
    expect(returned.status).toBe("NEEDS_REVISION");
    expect(reviewsOf(returned)[0]).toMatchObject({ by: "OTM", comment: "Natijani aniqroq yozing" });
  });

  it("keeps drafts as drafts", () => {
    expect(normalizeLog(backendLog({ status: "DRAFT" })).status).toBe("DRAFT");
  });
});

describe("date helpers", () => {
  it("uses the local calendar date and Monday-first grids", () => {
    expect(localISODate(new Date(2026, 10, 16, 0, 30))).toBe("2026-11-16");
    const grid = monthGrid("2026-11"); // 1 Nov 2026 is a Sunday
    expect(grid.slice(0, 7)).toEqual([null, null, null, null, null, null, "2026-11-01"]);
    expect(grid.length % 7).toBe(0);
    expect(weekdayOf("2026-11-16")).toBe(1);
    expect(longDate("2026-11-16")).toBe("16-noyabr, Dushanba");
    expect(addMonths("2026-12", 1)).toBe("2027-01");
  });
});

const slot = (weekday: number, start: number, end: number, subject: string, para = 1): ClassSlot => ({
  weekday,
  weekday_name: "",
  para_number: para,
  start_time: `${String(Math.floor(start / 60)).padStart(2, "0")}:${String(start % 60).padStart(2, "0")}`,
  end_time: `${String(Math.floor(end / 60)).padStart(2, "0")}:${String(end % 60).padStart(2, "0")}`,
  start_minute: start,
  end_minute: end,
  subject_name: subject,
  lesson_type: "MA'RUZA",
  room: "A-101",
  teacher_name: "A. Karimov",
});
const SLOTS = [slot(1, 510, 590, "Oliy matematika", 1), slot(1, 600, 680, "Dasturlash", 2), slot(3, 510, 590, "Fizika", 1)];

describe("timetable helpers", () => {
  it("finds work hours that clash with lessons", () => {
    expect(workClashes(SLOTS, 1, "09:00", "12:00").map((s) => s.subject_name)).toEqual(["Oliy matematika", "Dasturlash"]);
    expect(workClashes(SLOTS, 1, "12:00", "17:00")).toEqual([]);
    expect(workClashes(SLOTS, 1, "bad", "17:00")).toEqual([]);
  });

  it("returns the class in progress, then the next one", () => {
    const monday = (h: number, m: number) => new Date(2026, 10, 16, h, m);
    expect(currentOrNext(SLOTS, monday(8, 40))).toMatchObject({ inProgress: true, slot: { subject_name: "Oliy matematika" } });
    expect(currentOrNext(SLOTS, monday(9, 55))).toMatchObject({ inProgress: false, slot: { subject_name: "Dasturlash" } });
    expect(currentOrNext(SLOTS, monday(18, 0))).toBeNull();
    expect(classesOn(SLOTS, 3)).toHaveLength(1);
  });
});

describe("DiaryCalendar", () => {
  it("marks entry statuses, blocks days outside the placement and selects a day", () => {
    const onSelect = vi.fn();
    const logs = [normalizeLog(backendLog({ workplace_reviews: [{ decision: "APPROVED", decided_at: "2026-11-17" }] }))];
    render(
      <DiaryCalendar month="2026-11" onMonthChange={vi.fn()} logs={logs} selected="2026-11-16" onSelect={onSelect} minDate="2026-11-03" maxDate="2026-11-18" today="2026-11-18" />
    );
    expect(screen.getByRole("button", { name: "2026-11-16, Tasdiqlangan" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "2026-11-02" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "2026-11-20" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "2026-11-10" }));
    expect(onSelect).toHaveBeenCalledWith("2026-11-10");
    expect(screen.getByRole("button", { name: "Oldingi oy" })).toBeDisabled();
  });
});

const timetable = (over: Partial<MyTimetable> = {}): MyTimetable => ({
  status: "OK",
  institution_name: "TATU",
  program: "Dasturiy injiniring",
  group_code: "DI-21-01",
  matched_by: "PROGRAM",
  academic_semester: "2026-2027 kuzgi",
  updated_at: null,
  commute_buffer_minutes: 30,
  slots: SLOTS,
  free_windows: [{ weekday: 1, weekday_name: "Dushanba", class_count: 2, free_intervals: [{ start_minute: 710, end_minute: 1200, start_time: "11:50", end_time: "20:00", duration_minutes: 490 }] }],
  ...over,
});

describe("StudentTimetable", () => {
  it("shows the next lesson, today's list and the weekly load", () => {
    render(<StudentTimetable data={timetable()} now={new Date(2026, 10, 16, 9, 55)} />);
    expect(screen.getByRole("heading", { level: 1, name: "O‘quv jadvali" })).toBeInTheDocument();
    expect(screen.getByText("Guruh DI-21-01 · Dasturiy injiniring · 2026-2027 kuzgi")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Keyingi dars" })).toBeInTheDocument();
    expect(screen.getAllByText("Dasturlash").length).toBeGreaterThan(0);
    expect(screen.getAllByText("11:50–20:00").length).toBeGreaterThan(0);
  });

  it("explains why nothing is shown for an unverified student", () => {
    render(<StudentTimetable data={timetable({ status: "NO_VERIFIED_ENROLLMENT", slots: [], free_windows: [] })} />);
    expect(screen.getByText("Talabaligingiz hali tasdiqlanmagan")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Profilga o‘tish" })).toHaveAttribute("href", "/nomzod");
  });

  it("warns when the group was not matched from the programme", () => {
    render(<StudentTimetable data={timetable({ matched_by: "DEFAULT" })} now={new Date(2026, 10, 16, 9, 0)} />);
    expect(screen.getByText(/Guruhingiz yo‘nalish nomidan aniqlanmadi/)).toBeInTheDocument();
  });
});
