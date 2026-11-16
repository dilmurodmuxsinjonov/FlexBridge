import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchEnrollmentRequests: vi.fn(),
  claimEnrollmentRequest: vi.fn(),
  fetchEnrollmentRequestDetail: vi.fn(),
  openEnrollmentEvidence: vi.fn(),
  decideEnrollmentRequest: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

import EnrollmentRequestsPanel from "./EnrollmentRequestsPanel";

const item = {
  case_id: "case-1",
  enrollment_id: "enr-1",
  status: "PENDING",
  current_revision: 2,
  due_at: null,
  student_name: "Aziza Karimova",
  program: "Dasturiy injiniring",
  start_date: "2024-09-01",
  end_date: null,
  submitted_at: "2026-11-15T10:00:00Z",
  assigned_to_me: false,
  claimed_by_other: false,
};

describe("EnrollmentRequestsPanel", () => {
  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset());
    api.fetchEnrollmentRequests.mockResolvedValue([item]);
    api.claimEnrollmentRequest.mockResolvedValue(undefined);
    api.fetchEnrollmentRequestDetail.mockResolvedValue({
      case: { id: "case-1", status: "IN_REVIEW", current_revision: 2 },
      submissions: [
        { revision: 2, program: "Dasturiy injiniring", start_date: "2024-09-01", end_date: null, evidence_note: "Ma’lumotnoma", files: [{ id: "f1", sha256: "x", byte_size: 2048, download_path: null }] },
      ],
      decisions: [],
    });
    api.decideEnrollmentRequest.mockResolvedValue(undefined);
  });

  it("explains when the user is not a coordinator anywhere", () => {
    render(<EnrollmentRequestsPanel institutionId={null} />);
    expect(screen.getByText(/biriktirilmagansiz/)).toBeInTheDocument();
    expect(api.fetchEnrollmentRequests).not.toHaveBeenCalled();
  });

  it("claims, shows evidence and submits a decision for the current revision", async () => {
    render(<EnrollmentRequestsPanel institutionId="inst-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Aziza Karimova/ }));

    await screen.findByRole("button", { name: /Hujjat 1/ });
    expect(api.claimEnrollmentRequest).toHaveBeenCalledWith("inst-1", "case-1");

    fireEvent.change(screen.getByLabelText(/Izoh/), { target: { value: "Dekanat ro‘yxati bilan solishtirildi." } });
    fireEvent.click(screen.getByRole("button", { name: /Qarorni saqlash/ }));

    await waitFor(() =>
      expect(api.decideEnrollmentRequest).toHaveBeenCalledWith("inst-1", "case-1", {
        decision: "APPROVE",
        expected_revision: 2,
        reason: "Dekanat ro‘yxati bilan solishtirildi.",
      })
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Aziza Karimova");
  });

  it("requires a meaningful reason before deciding", async () => {
    render(<EnrollmentRequestsPanel institutionId="inst-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Aziza Karimova/ }));
    await screen.findByRole("button", { name: /Hujjat 1/ });
    fireEvent.click(screen.getByRole("button", { name: /Qarorni saqlash/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/15 belgi/);
    expect(api.decideEnrollmentRequest).not.toHaveBeenCalled();
  });
});
