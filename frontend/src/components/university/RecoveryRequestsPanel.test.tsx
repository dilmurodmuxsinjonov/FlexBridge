import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ fetchRecoveryRequests: vi.fn(), decideRecoveryRequest: vi.fn() }));
vi.mock("@/lib/universityStaff", async (orig) => ({ ...(await orig<typeof import("@/lib/universityStaff")>()), ...api }));

import RecoveryRequestsPanel from "./RecoveryRequestsPanel";
import { StaffApiError } from "@/lib/universityStaff";

const INST = "11111111-1111-4111-8111-111111111111";
const item = {
  id: "r-1",
  created_at: "2026-11-16T09:00:00Z",
  student_name: "Aziza Karimova",
  contacts: [{ channel: "PHONE" as const, masked: "+99890***4567" }],
};

describe("RecoveryRequestsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.fetchRecoveryRequests.mockResolvedValue({ items: [item], approval_valid_hours: 72 });
  });

  it("approves only with a written identity check and refreshes the queue", async () => {
    api.decideRecoveryRequest.mockResolvedValue({ id: "r-1", status: "APPROVED", valid_until: "2026-11-19T09:00:00Z" });
    render(<RecoveryRequestsPanel institutionId={INST} />);
    expect(await screen.findByText("Aziza Karimova")).toBeInTheDocument();
    expect(screen.getByText(/\+99890\*\*\*4567/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ko‘rib chiqish" }));
    const approve = screen.getByRole("button", { name: /Shaxsi tasdiqlandi/ });
    expect(approve).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Qanday tekshirdingiz?"), { target: { value: "Dekanatda pasporti bilan tekshirildi" } });
    api.fetchRecoveryRequests.mockResolvedValue({ items: [], approval_valid_hours: 72 });
    fireEvent.click(approve);
    await waitFor(() =>
      expect(api.decideRecoveryRequest).toHaveBeenCalledWith(INST, "r-1", "APPROVE", "Dekanatda pasporti bilan tekshirildi")
    );
    expect(await screen.findByText(/Tasdiqlandi. Talaba 72 soat/)).toBeInTheDocument();
    expect(await screen.findByText("Hozircha so‘rovlar yo‘q.")).toBeInTheDocument();
  });

  it("explains refusals in plain language", async () => {
    api.decideRecoveryRequest.mockRejectedValue(new StaffApiError("RECOVERY_REQUEST_NOT_AVAILABLE", 404));
    render(<RecoveryRequestsPanel institutionId={INST} />);
    fireEvent.click(await screen.findByRole("button", { name: "Ko‘rib chiqish" }));
    fireEvent.change(screen.getByLabelText("Qanday tekshirdingiz?"), { target: { value: "Telefon orqali tekshirildi, ma’lumotlar mos" } });
    fireEvent.click(screen.getByRole("button", { name: "Rad etish" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("allaqachon ko‘rib chiqilgan");
  });

  it("renders nothing without an institution", () => {
    const { container } = render(<RecoveryRequestsPanel institutionId={null} />);
    expect(container).toBeEmptyDOMElement();
    expect(api.fetchRecoveryRequests).not.toHaveBeenCalled();
  });
});
