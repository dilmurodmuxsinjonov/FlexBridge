import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OperatorOverview, { attentionItems, type OperatorOverviewProps } from "./OperatorOverview";

const past = new Date(Date.now() - 86_400_000).toISOString();
function props(over: Partial<OperatorOverviewProps> = {}): OperatorOverviewProps {
  return {
    name: "Rustam Aliyev",
    roles: ["MODERATOR", "SUPPORT"],
    visible: ["VERIFICATION", "SUPPORT_OPS"],
    cases: [
      { id: "c1", status: "OPEN", organization_name: "Uzum Tech", due_at: past },
      { id: "c2", status: "APPROVED", organization_name: "EPAM" },
      { id: "c3", status: "IN_REVIEW", institution_name: "TATU" },
    ],
    tickets: [
      { id: "t1", category: "TECHNICAL", status: "OPEN", priority: "URGENT", created_at: past },
      { id: "t2", category: "BILLING", status: "IN_PROGRESS", priority: "LOW", created_at: past },
      { id: "t3", category: "ACCOUNT", status: "RESOLVED", priority: "URGENT", created_at: past },
    ],
    auditEvents: [],
    discrepancies: 2,
    onOpen: vi.fn(),
    today: new Date(2026, 10, 17, 9, 0),
    ...over,
  };
}

describe("OperatorOverview", () => {
  it("greets by name and shows role labels in Uzbek", () => {
    render(<OperatorOverview {...props()} />);
    expect(screen.getByText("Salom, Rustam")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Operator paneli" })).toBeInTheDocument();
    expect(screen.getByText("Moderator, Yordam xizmati")).toBeInTheDocument();
  });

  it("counts open cases and open tickets by priority", () => {
    render(<OperatorOverview {...props()} />);
    const cases = screen.getByRole("heading", { name: "Tekshiruv navbati" }).closest("section")!;
    expect(within(cases).getByText("2")).toBeInTheDocument();
    expect(within(cases).getByText("Uzum Tech")).toBeInTheDocument();
    const tickets = screen.getByRole("heading", { name: "Murojaatlar" }).closest("section")!;
    expect(within(tickets).getByText("Jami 2 ta ochiq")).toBeInTheDocument();
  });

  it("lists only what this role can act on and opens it", () => {
    const onOpen = vi.fn();
    render(<OperatorOverview {...props({ onOpen })} />);
    const att = screen.getByRole("heading", { name: "Diqqat talab qiladi" }).closest("section")!;
    expect(within(att).getByText("muhim murojaat (shoshilinch / yuqori)")).toBeInTheDocument();
    expect(within(att).getByText("tekshiruv muddati o‘tgan")).toBeInTheDocument();
    expect(within(att).queryByText("to‘lovda nomuvofiqlik")).not.toBeInTheDocument(); // FINANCE not visible
    fireEvent.click(within(att).getByRole("button", { name: /muhim murojaat/ }));
    expect(onOpen).toHaveBeenCalledWith("SUPPORT_OPS");
  });

  it("hides cards for modules the role cannot open", () => {
    render(<OperatorOverview {...props({ visible: ["FINANCE"] })} />);
    expect(screen.queryByRole("heading", { name: "Tekshiruv navbati" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Murojaatlar" })).not.toBeInTheDocument();
    expect(screen.getByText("to‘lovda nomuvofiqlik")).toBeInTheDocument();
  });

  it("reports nothing urgent when there is nothing to do", () => {
    expect(attentionItems({ cases: [], tickets: [], discrepancies: 0, visible: ["VERIFICATION", "SUPPORT_OPS", "FINANCE"] })).toEqual([]);
  });

  it("shows Super Admin quick navigation cards and opens governance sections", () => {
    const onOpen = vi.fn();
    const onOpenGovernance = vi.fn();
    render(
      <OperatorOverview
        {...props({
          roles: ["ADMIN"],
          visible: ["STAFF_ROLES", "FEATURE_FLAGS", "DIRECTORY", "GOVERNANCE", "AUDIT"],
          activeStaffGrantsCount: 4,
          enabledR1FlagsCount: 2,
          pendingRecoveryCount: 3,
          onOpen,
          onOpenGovernance,
        })}
      />
    );
    expect(screen.getByText("4 ta faol vakolat")).toBeInTheDocument();
    expect(screen.getByText("2 ta R1 flag faol")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Xodim rollari va matritsa/ }));
    expect(onOpen).toHaveBeenCalledWith("STAFF_ROLES");
    fireEvent.click(screen.getByRole("button", { name: /parol tiklash so‘rovi/ }));
    expect(onOpenGovernance).toHaveBeenCalledWith("RECOVERY");
  });
});
