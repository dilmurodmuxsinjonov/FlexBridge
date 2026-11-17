import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProfileOverview, { readinessItems, type ProfileOverviewProps } from "./ProfileOverview";
import ProfileCard from "./ProfileCard";
import { initials, isoWeekday, uzDate } from "@/lib/person";

// 2026-11-16 is a Monday (ISO weekday 1).
const MONDAY = new Date(2026, 10, 16, 10, 0, 0);

function props(over: Partial<ProfileOverviewProps> = {}): ProfileOverviewProps {
  return {
    name: "Dilnoza Karimova",
    headline: "Frontend dasturchi (amaliyotchi)",
    region: "Toshkent",
    skills: [
      { skill_id: "s1", level: "INTERMEDIATE", code: "REACT", name_uz: "React", name_ru: "React", active: true, verified: true },
      { skill_id: "s2", level: "BEGINNER", code: "SQL", name_uz: "SQL", name_ru: "SQL", active: true },
    ],
    rules: [
      { weekday: 1, start_minute: 14 * 60, end_minute: 18 * 60 },
      { weekday: 3, start_minute: 9 * 60, end_minute: 12 * 60 },
    ],
    enrollments: [],
    portfolios: [],
    certificates: [],
    experiences: [],
    applications: {
      contract_id: "API-029",
      candidate_id: "c",
      total_applications: 6,
      submitted: 2,
      under_review: 1,
      interview_scheduled: 1,
      interviews_total: 1,
      offered: 1,
      offers_total: 1,
      accepted: 0,
      rejected: 1,
      withdrawn: 0,
      expired: 0,
    },
    isExporting: false,
    onExport: vi.fn(),
    onOpenTab: vi.fn(),
    today: MONDAY,
    ...over,
  };
}

describe("person helpers", () => {
  it("builds initials, ISO weekday and an Uzbek date", () => {
    expect(initials("Dilnoza Karimova")).toBe("DK");
    expect(initials("  ")).toBe("FB");
    expect(isoWeekday(MONDAY)).toBe(1);
    expect(isoWeekday(new Date(2026, 10, 15))).toBe(7);
    expect(uzDate(MONDAY)).toBe("16-noyabr, Dushanba");
  });
});

describe("ProfileOverview", () => {
  it("greets by first name and shows headline, region and readiness from real data", () => {
    render(<ProfileOverview {...props()} />);
    expect(screen.getByText("Salom, Dilnoza")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Mening profilim" })).toBeInTheDocument();
    expect(screen.getByText("Frontend dasturchi (amaliyotchi) · Toshkent")).toBeInTheDocument();
    // headline + skills + schedule = 3 of 5
    expect(screen.getByText("60")).toBeInTheDocument();
    expect(screen.getByText("5 tadan 3 bo‘lim tayyor")).toBeInTheDocument();
  });

  it("draws one bar per availability window and marks today", () => {
    render(<ProfileOverview {...props()} />);
    const monday = screen.getByTitle("Dushanba: 14:00–18:00");
    expect(monday.className).toContain("fb-bar-today");
    expect(screen.getByTitle("Chorshanba: 09:00–12:00").className).not.toContain("fb-bar-today");
    expect(screen.getByText("Ish uchun haftasiga 7 soat")).toBeInTheDocument();
  });

  it("offers to fill the schedule instead of drawing an empty chart", () => {
    const onOpenTab = vi.fn();
    render(<ProfileOverview {...props({ rules: [], onOpenTab })} />);
    fireEvent.click(screen.getByRole("button", { name: "Jadvalni to‘ldirish" }));
    expect(onOpenTab).toHaveBeenCalledWith("AVAILABILITY");
  });

  it("opens the tab that fixes a missing readiness item", () => {
    const onOpenTab = vi.fn();
    render(<ProfileOverview {...props({ onOpenTab })} />);
    const card = screen.getByRole("heading", { name: "Profil tayyorligi" }).closest("section")!;
    fireEvent.click(within(card).getByRole("button", { name: /Talabalik tasdig‘i/ }));
    expect(onOpenTab).toHaveBeenCalledWith("ENROLLMENTS");
  });

  it("shows application counts and the verified-skill ratio", () => {
    render(<ProfileOverview {...props()} />);
    const apps = screen.getByRole("heading", { name: "Arizalarim" }).closest("section")!;
    expect(within(apps).getByText("Jami arizalar").nextElementSibling?.textContent).toContain("6");
    expect(within(apps).getByText("Ko‘rib chiqilmoqda").nextElementSibling?.textContent).toContain("3");
    expect(screen.getByText("1/2")).toBeInTheDocument();
  });

  it("reports a failed applications load instead of showing zeros", () => {
    render(<ProfileOverview {...props({ applications: null, applicationsError: true })} />);
    expect(screen.getByText("Arizalar statistikasini hozir yuklab bo‘lmadi.")).toBeInTheDocument();
  });

  it("exports the resume from the resume card", () => {
    const onExport = vi.fn();
    render(<ProfileOverview {...props({ onExport })} />);
    fireEvent.click(screen.getByRole("button", { name: "Yuklab olish" }));
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it("counts readiness items independently", () => {
    const items = readinessItems({ headline: "", skills: [], rules: [], enrollments: [], experiences: [], portfolios: [] });
    expect(items.every((i) => !i.done)).toBe(true);
  });
});

describe("ProfileCard", () => {
  it("shows the name and a keyboard-accessible account menu", () => {
    const onLogout = vi.fn();
    render(<ProfileCard name="Dilnoza Karimova" roleLabel="Talaba · nomzod" securityHref="/nomzod/xavfsizlik" onLogout={onLogout} />);
    expect(screen.getByText("Dilnoza Karimova")).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Hisob menyusini ochish" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Xavfsizlik" })).toHaveAttribute("href", "/nomzod/xavfsizlik");
    fireEvent.click(screen.getByRole("button", { name: "Chiqish" }));
    expect(onLogout).toHaveBeenCalled();
  });
});
