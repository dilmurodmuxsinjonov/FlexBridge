import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const staff = vi.hoisted(() => ({
  fetchStaff: vi.fn(),
  fetchMyVerifiedContacts: vi.fn(),
  uploadStaffPdf: vi.fn(),
  submitAppointment: vi.fn(),
  revokeAppointment: vi.fn(),
}));
vi.mock("@/lib/universityStaff", async (orig) => ({ ...(await orig<typeof import("@/lib/universityStaff")>()), ...staff }));

import UniversityStaffPanel from "./UniversityStaffPanel";
import { StaffApiError, describeStaffError } from "@/lib/universityStaff";

const INST = "11111111-1111-4111-8111-111111111111";
const overview = {
  institution: { id: INST, name: "TATU", status: "VERIFIED", registry_code: "INST-1" },
  agreement: { id: "agr-1", version: 1, status: "ACTIVE", valid_from: "2026-01-01", valid_to: null },
  items: [
    { id: "a-1", display_name: "Dekan Aliyev", mode: "FIRST_COORDINATOR", role: "COORDINATOR", is_self: true, status: "ACTIVE", case_status: "APPROVED",
      decision_reason: null, revision: 1, valid_from: "2026-01-01", valid_to: null, accepted_at: "2026-01-02", created_at: "2026-01-01", role_active: true },
    { id: "a-2", display_name: "Olimova Dilnoza", mode: "STAFF_TEACHER", role: "TEACHER", is_self: false, status: "PENDING_REVIEW", case_status: "PENDING",
      decision_reason: null, revision: 1, valid_from: "2026-09-01", valid_to: "2027-06-30", accepted_at: null, created_at: "2026-09-01", role_active: false },
  ],
};

describe("UniversityStaffPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    staff.fetchStaff.mockResolvedValue(overview);
    staff.fetchMyVerifiedContacts.mockResolvedValue([{ id: "c-1", channel: "EMAIL", masked_destination: "de***@tatu.uz", is_primary: true }]);
  });

  it("lists staff with readable roles and statuses, and no revoke on self", async () => {
    render(<UniversityStaffPanel institutionId={INST} />);
    expect(await screen.findByText("Olimova Dilnoza")).toBeInTheDocument();
    expect(screen.getByText("Platforma tekshiruvida")).toBeInTheDocument();
    expect(screen.getByText("Koordinator")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /bekor qilish/i })).toHaveLength(1);
  });

  it("adds a teacher: uploads the order, then submits a staff request for the institution", async () => {
    staff.uploadStaffPdf.mockResolvedValue({ file_id: "f-1", filename: "buyruq.pdf" });
    staff.submitAppointment.mockResolvedValue({ id: "a-3", mode: "STAFF_TEACHER", status: "PENDING_REVIEW", case_status: "PENDING" });
    render(<UniversityStaffPanel institutionId={INST} />);
    fireEvent.click(await screen.findByRole("button", { name: /Xodim qo‘shish/ }));
    fireEvent.change(screen.getByLabelText("Xodimning telefon raqami yoki pochtasi"), { target: { value: "90 123 45 67" } });
    const pdf = new File(["%PDF-1.4"], "buyruq.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("Tayinlov hujjati (PDF)"), { target: { files: [pdf] } });
    fireEvent.change(screen.getByLabelText("Huquqiy asos"), { target: { value: "Rektorning 245-son buyrug‘i, 01.09.2026" } });
    fireEvent.change(screen.getByLabelText("Tekshiruvchi uchun izoh"), { target: { value: "Kafedra o‘qituvchisi, amaliyot rahbari" } });
    fireEvent.click(screen.getByRole("button", { name: /So‘rov yuborish/ }));
    await waitFor(() => expect(staff.submitAppointment).toHaveBeenCalled());
    const [body, key] = staff.submitAppointment.mock.calls[0];
    expect(staff.uploadStaffPdf).toHaveBeenCalledWith(pdf, "INSTITUTION_APPOINTMENT");
    expect(body).toMatchObject({
      registry_code: "INST-1",
      agreement_id: "agr-1",
      document_file_id: "f-1",
      file_ids: ["f-1"],
      contact_id: "c-1",
      target_channel: "PHONE",
      target_destination: "+998901234567",
    });
    expect(String(key)).toMatch(/^staff-/);
    expect(await screen.findByText(/So‘rov yuborildi/)).toBeInTheDocument();
  });

  it("revokes with a reason and explains backend refusals", async () => {
    staff.revokeAppointment.mockRejectedValue(new StaffApiError("MFA_REQUIRED", 403));
    render(<UniversityStaffPanel institutionId={INST} />);
    fireEvent.click(await screen.findByRole("button", { name: /So‘rovni bekor qilish/ }));
    const confirm = screen.getByRole("button", { name: "Tasdiqlash" });
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Bekor qilish sababi"), { target: { value: "Universitetdan ishdan bo‘shadi" } });
    fireEvent.click(confirm);
    await waitFor(() => expect(staff.revokeAppointment).toHaveBeenCalledWith("a-2", "Universitetdan ishdan bo‘shadi"));
    expect(await screen.findByRole("alert")).toHaveTextContent("ikki bosqichli himoya");
  });

  it("blocks adding staff without a current agreement", async () => {
    staff.fetchStaff.mockResolvedValue({ ...overview, agreement: null });
    render(<UniversityStaffPanel institutionId={INST} />);
    expect(await screen.findByText(/amaldagi shartnomasi topilmadi/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Xodim qo‘shish/ })).toBeDisabled();
  });
});

describe("describeStaffError", () => {
  it("never shows raw codes", () => {
    expect(describeStaffError(new StaffApiError("INSTITUTION_TARGET_UNAVAILABLE", 403))).toMatch(/ro‘yxatdan o‘tib/);
    expect(describeStaffError(new StaffApiError("SOMETHING_NEW", 500))).not.toContain("SOMETHING_NEW");
  });
});
