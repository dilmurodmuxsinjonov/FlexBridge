import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import EmployerOverview, { funnelStages, type EmployerOverviewProps } from "./EmployerOverview";

const metrics = {
  opportunities: { total: 6, published: 3, draft: 2, closed: 1, paused: 0 },
  applications: { total: 40, pending: 12, shortlisted: 18, interviewed: 9, offered: 5, accepted: 4, rejected: 10, withdrawn: 2 },
  engagements: { total: 6, active: 4, pending_start: 1, completed: 1, disputed: 0 },
  interviews: { total: 11, scheduled: 3, completed: 8, cancelled: 0, no_show: 0 },
};

const opp = (id: string, title: string, status: string, apps: number) => ({
  id,
  title,
  kind: "INTERNSHIP",
  status,
  region: "Toshkent",
  work_mode: "HYBRID",
  capacity: 5,
  occupied_count: 2,
  applications_count: apps,
  published_at: null,
  expires_at: null,
  created_at: null,
});

function props(over: Partial<EmployerOverviewProps> = {}): EmployerOverviewProps {
  return {
    name: "Jamshid Qodirov",
    orgName: "Uzum Tech",
    orgRegion: "Toshkent",
    roles: ["OWNER"],
    metrics,
    opportunities: [opp("o1", "Backend amaliyotchi", "PUBLISHED", 21), opp("o2", "QA stajyor", "PUBLISHED", 9), opp("o3", "Dizayner", "DRAFT", 0)],
    mentorQueue: [],
    onOpen: vi.fn(),
    onOpenOpportunity: vi.fn(),
    onCreate: vi.fn(),
    today: new Date(2026, 10, 16, 10, 0),
    ...over,
  };
}

describe("funnelStages", () => {
  it("follows applications through the hiring stages", () => {
    expect(funnelStages(metrics).map((s) => s.value)).toEqual([40, 18, 9, 5, 4]);
  });
});

describe("EmployerOverview", () => {
  it("greets by name and shows company, role and funnel conversion", () => {
    render(<EmployerOverview {...props()} />);
    expect(screen.getByText("Salom, Jamshid")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Korxona paneli" })).toBeInTheDocument();
    expect(screen.getByText("Uzum Tech · Toshkent")).toBeInTheDocument();
    expect(screen.getByText("Asosiy egasi")).toBeInTheDocument();
    expect(screen.getByText("Arizalarning 10% qabul bilan yakunlangan · 12 ta javob kutmoqda")).toBeInTheDocument();
  });

  it("highlights the published vacancy with the most applications and opens it", () => {
    const onOpenOpportunity = vi.fn();
    render(<EmployerOverview {...props({ onOpenOpportunity })} />);
    const top = screen.getByRole("heading", { name: "Eng faol vakansiya" }).closest("section")!;
    expect(within(top).getByText("Backend amaliyotchi")).toBeInTheDocument();
    expect(within(top).getByText("2/5")).toBeInTheDocument();
    fireEvent.click(within(top).getByRole("button", { name: /Arizalarni ko‘rish/ }));
    expect(onOpenOpportunity).toHaveBeenCalledWith("o1");
  });

  it("labels vacancy statuses in Uzbek and creates from the header", () => {
    const onCreate = vi.fn();
    render(<EmployerOverview {...props({ onCreate })} />);
    const list = screen.getByRole("heading", { name: "E’lonlarim" }).closest("section")!;
    expect(within(list).getByText("Qoralama · 0 ariza")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /Yangi e’lon/ })[0]);
    expect(onCreate).toHaveBeenCalled();
  });

  it("invites to post when nothing is published", () => {
    render(<EmployerOverview {...props({ opportunities: [opp("o3", "Dizayner", "DRAFT", 0)] })} />);
    expect(screen.getByText("Faol e’lon yo‘q")).toBeInTheDocument();
  });

  it("shows only the header until the dashboard loads", () => {
    render(<EmployerOverview {...props({ metrics: null })} />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.queryByText("Nabor voronkasi")).not.toBeInTheDocument();
  });
});
