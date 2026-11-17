import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import UniversityOverview, { oldestWaitDays, queueByDay, type UniversityOverviewProps } from "./UniversityOverview";
import type { AcademicReviewQueueItem } from "@/lib/api";

const MONDAY = new Date(2026, 10, 16, 10, 0);
const q = (id: string, submitted: string, name = "Aziz Rahimov"): AcademicReviewQueueItem => ({
  id,
  daily_log_id: `l-${id}`,
  placement_id: "p",
  institution_id: "i",
  purpose: "ACADEMIC_REVIEW",
  local_date: submitted.slice(0, 10),
  revision: 1,
  submitted_at: submitted,
  student_name: name,
});

function props(over: Partial<UniversityOverviewProps> = {}): UniversityOverviewProps {
  return {
    name: "Nodira Yusupova",
    institutionName: "TATU",
    institutionRegion: "Toshkent",
    isCoordinator: true,
    queue: [q("a", "2026-11-16T08:00:00"), q("b", "2026-11-14T08:00:00", "Laylo Karimova"), q("c", "2026-11-01T08:00:00", "Bekzod Aliyev")],
    assignments: [
      { id: "s1", placement_id: "p1", institution_id: "i", assigned_at: "2026-11-01", accepted_at: "2026-11-02", student_name: "Aziz Rahimov" },
      { id: "s2", placement_id: "p2", institution_id: "i", assigned_at: "2026-11-01", accepted_at: null, student_name: "Laylo Karimova" },
      { id: "s3", placement_id: "p3", institution_id: "i", assigned_at: "2026-11-01", accepted_at: "2026-11-03", student_name: "Bekzod Aliyev" },
    ],
    coordinatorQueue: [{ id: "c1", request_revision: 1, placement_id: "p4", enrollment_id: "e", institution_id: "i", terms_id: "t", student_name: "Dilnoza Karimova" }],
    teachersCount: 4,
    timetable: null,
    onOpen: vi.fn(),
    today: MONDAY,
    ...over,
  };
}

describe("queue helpers", () => {
  it("buckets the last 7 days and folds older items into the first day", () => {
    const days = queueByDay(props().queue, MONDAY);
    expect(days.map((d) => d.count)).toEqual([1, 0, 0, 0, 1, 0, 1]);
    expect(oldestWaitDays(props().queue, MONDAY)).toBe(15);
    expect(oldestWaitDays([], MONDAY)).toBeNull();
  });
});

describe("UniversityOverview", () => {
  it("greets the coordinator and shows coverage from real counts", () => {
    render(<UniversityOverview {...props()} />);
    expect(screen.getByText("Salom, Nodira")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Akademik panel" })).toBeInTheDocument();
    expect(screen.getByText("TATU · Toshkent")).toBeInTheDocument();
    const cover = screen.getByRole("heading", { name: "Biriktiruv qamrovi" }).closest("section")!;
    expect(within(cover).getByText("75")).toBeInTheDocument(); // 3 assigned of 4
    expect(screen.getByText("Jami 3 ta · eng eskisi 15 kundan beri kutmoqda")).toBeInTheDocument();
  });

  it("points at the oldest diary and opens the queue", () => {
    const onOpen = vi.fn();
    render(<UniversityOverview {...props({ onOpen })} />);
    const next = screen.getByRole("heading", { name: "Navbatdagi ko‘rik" }).closest("section")!;
    expect(within(next).getByText("Bekzod Aliyev")).toBeInTheDocument();
    fireEvent.click(within(next).getByRole("button", { name: /Ko‘rib chiqish/ }));
    expect(onOpen).toHaveBeenCalledWith("queue");
  });

  it("shows a teacher their own students instead of department tools", () => {
    render(<UniversityOverview {...props({ isCoordinator: false })} />);
    expect(screen.getByRole("heading", { name: "Mening talabalarim" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Talabalarim" })).toBeInTheDocument();
    expect(screen.queryByText("Rahbar kutmoqda")).not.toBeInTheDocument();
    expect(screen.getByText("O‘qituvchi")).toBeInTheDocument();
  });

  it("handles an empty queue and a missing timetable honestly", () => {
    render(<UniversityOverview {...props({ queue: [], timetable: null })} />);
    expect(screen.getByText("Hammasi ko‘rib chiqilgan")).toBeInTheDocument();
    expect(screen.getByText("Navbat bo‘sh — hamma kundaliklar ko‘rib chiqilgan.")).toBeInTheDocument();
    expect(screen.getByText("Jadval hali kiritilmagan")).toBeInTheDocument();
  });

  it("reports a failed queue load instead of an empty chart", () => {
    render(<UniversityOverview {...props({ queue: [], queueError: "x" })} />);
    expect(screen.getByText("Navbatni yuklab bo‘lmadi.")).toBeInTheDocument();
  });
});
