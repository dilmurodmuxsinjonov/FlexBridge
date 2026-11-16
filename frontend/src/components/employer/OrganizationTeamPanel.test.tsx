import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchTeam: vi.fn(),
  createInvitation: vi.fn(),
  revokeInvitation: vi.fn(),
  approveJoin: vi.fn(),
  removeMember: vi.fn(),
}));
vi.mock("@/lib/orgTeam", async (orig) => ({ ...(await orig<typeof import("@/lib/orgTeam")>()), ...api }));

import OrganizationTeamPanel from "./OrganizationTeamPanel";
import { StaffApiError } from "@/lib/universityStaff";

const ORG = "22222222-2222-4222-8222-222222222222";
const team = {
  organization: { id: ORG, public_name: "Misol Soft", legal_name: "Misol Soft MChJ", status: "VERIFIED", tax_id: "123456789", region: "Toshkent" },
  members: [
    { membership_id: "m-1", display_name: "Rahbar Aliyev", status: "ACTIVE", roles: ["OWNER"], is_self: true, created_at: "2026-11-01", accepted_at: "2026-11-01", revoked_at: null },
    { membership_id: "m-2", display_name: "Dilnoza HR", status: "ACTIVE", roles: ["HR"], is_self: false, created_at: "2026-11-02", accepted_at: "2026-11-02", revoked_at: null },
  ],
  join_requests: [
    { membership_id: "m-3", display_name: "Jasur Mentor", status: "PENDING_APPROVAL", roles: [], is_self: false, created_at: "2026-11-10", accepted_at: null, revoked_at: null, requested_role: "MENTOR", self_join: true },
  ],
  invitations: [{ id: "i-1", role_code: "BILLING", channel: "EMAIL", created_at: "2026-11-15", expires_at: "2026-11-16T12:00:00Z" }],
};

describe("OrganizationTeamPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchTeam.mockResolvedValue(team);
  });

  it("shows people by name with readable roles, requests and invitations", async () => {
    render(<OrganizationTeamPanel orgId={ORG} />);
    expect(await screen.findByText("Dilnoza HR")).toBeInTheDocument();
    expect(screen.getByText("Rahbar (asosiy akkaunt)")).toBeInTheDocument();
    expect(screen.getAllByText("HR mutaxassis").some((el) => el.tagName === "SPAN")).toBe(true);
    expect(screen.getByText(/So‘ralgan rol: Mentor/)).toBeInTheDocument();
    expect(screen.getByText("Javob kutilayotgan takliflar")).toBeInTheDocument();
    expect(screen.getAllByText(/Moliya \/ to‘lovlar/).some((el) => el.tagName === "DIV")).toBe(true);
    // The owner cannot remove themself; HR can be removed.
    expect(screen.getAllByRole("button", { name: /Chiqarish/ })).toHaveLength(1);
  });

  it("creates an invitation and shows a shareable link", async () => {
    api.createInvitation.mockResolvedValue({ id: "i-2", token: "T".repeat(43), expires_at: "", role_code: "MENTOR" });
    render(<OrganizationTeamPanel orgId={ORG} />);
    await screen.findByText("Dilnoza HR");
    fireEvent.change(screen.getByLabelText("Xodimning telefoni yoki pochtasi"), { target: { value: "90 123 45 67" } });
    fireEvent.change(screen.getByLabelText("Rol"), { target: { value: "MENTOR" } });
    fireEvent.click(screen.getByRole("button", { name: /Taklif havolasi/ }));
    await waitFor(() => expect(api.createInvitation).toHaveBeenCalledWith(ORG, "PHONE", "+998901234567", "MENTOR"));
    const link = (await screen.findByLabelText("Taklif havolasi")) as HTMLInputElement;
    expect(link.value).toMatch(/\/korxona\/royxatdan-otish\?token=T{43}$/);
  });

  it("approves a join request and explains refusals", async () => {
    api.approveJoin.mockResolvedValue({});
    render(<OrganizationTeamPanel orgId={ORG} />);
    const approve = await screen.findByRole("button", { name: "Tasdiqlash" });
    api.fetchTeam.mockResolvedValue({ ...team, join_requests: [] });
    fireEvent.click(approve);
    await waitFor(() => expect(api.approveJoin).toHaveBeenCalledWith(ORG, "m-3"));
    expect(await screen.findByText(/Jasur Mentor jamoaga qo‘shildi/)).toBeInTheDocument();

    api.removeMember.mockRejectedValue(new StaffApiError("LAST_OWNER_PROTECTED", 409));
    fireEvent.click(screen.getByRole("button", { name: /Chiqarish/ }));
    fireEvent.change(screen.getByLabelText("Sabab"), { target: { value: "Korxonadan ishdan bo‘shadi" } });
    fireEvent.click(screen.getByRole("button", { name: "Tasdiqlash" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("yagona rahbarini");
  });

  it("locks invitations while the company is under review", async () => {
    api.fetchTeam.mockResolvedValue({ ...team, organization: { ...team.organization, status: "PENDING_VERIFICATION" } });
    render(<OrganizationTeamPanel orgId={ORG} />);
    expect(await screen.findByText(/hali tekshiruvda/)).toBeInTheDocument();
    expect(screen.getByLabelText("Xodimning telefoni yoki pochtasi")).toBeDisabled();
  });
});
