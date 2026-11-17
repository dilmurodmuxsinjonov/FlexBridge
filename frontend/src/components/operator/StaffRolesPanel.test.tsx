import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchStaffGrants: vi.fn(),
  fetchDirectoryUsers: vi.fn(),
  grantStaffRole: vi.fn(),
  revokeStaffRole: vi.fn(),
}));

vi.mock("@/lib/platformAdmin", async (orig) => ({
  ...(await orig<typeof import("@/lib/platformAdmin")>()),
  ...api,
}));

import StaffRolesPanel from "./StaffRolesPanel";

const ADMIN_ID = "11111111-1111-4111-8111-111111111111";
const OTHER_ID = "22222222-2222-4222-8222-222222222222";
const CANDIDATE_ID = "33333333-3333-4333-8333-333333333333";

function grantsPayload() {
  return {
    ok: true,
    active_grants: [
      {
        id: "g-self-admin",
        user_id: ADMIN_ID,
        display_name: "Dilmurod Admin",
        masked_contact: "+998 90 *** 01 01",
        role_code: "ADMIN",
        granter_display_name: "FlexBridge System Authority",
        reason: "Dastlabki bosh administrator",
        is_permanent: true,
        expires_at: "2036-11-17T00:00:00Z",
      },
      {
        id: "g-mod",
        user_id: OTHER_ID,
        display_name: "Aziza Karimova",
        masked_contact: "+998 91 *** 22 33",
        role_code: "MODERATOR",
        granter_display_name: "Dilmurod Admin",
        reason: "E’lon va KYB tekshiruvchisi",
        is_permanent: true,
        expires_at: "2036-11-17T00:00:00Z",
      },
    ],
    recent_revoked: [],
  };
}

beforeEach(() => {
  api.fetchStaffGrants.mockReset();
  api.fetchDirectoryUsers.mockReset();
  api.grantStaffRole.mockReset();
  api.revokeStaffRole.mockReset();
});

describe("StaffRolesPanel", () => {
  it("renders the Uzbek role authority matrix with scope filters", async () => {
    api.fetchStaffGrants.mockResolvedValue(grantsPayload());
    render(<StaffRolesPanel currentUserId={ADMIN_ID} roles={["CANDIDATE", "SECURITY_LEAD"]} />);

    expect(screen.getByRole("heading", { name: "Rollar va vakolatlar matritsasi" })).toBeInTheDocument();
    expect(screen.getByText("Bosh administrator (Super Admin)")).toBeInTheDocument();
    expect(screen.getByText("Korxona asosiy egasi")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Korxona" }));
    expect(screen.getByText("Korxona asosiy egasi")).toBeInTheDocument();
    expect(screen.queryByText("Bosh administrator (Super Admin)")).not.toBeInTheDocument();
  });

  it("keeps SECURITY_LEAD in read-only mode without grant/revoke controls", async () => {
    api.fetchStaffGrants.mockResolvedValue(grantsPayload());
    render(<StaffRolesPanel currentUserId={ADMIN_ID} roles={["CANDIDATE", "SECURITY_LEAD"]} />);

    expect(await screen.findByText("Aziza Karimova")).toBeInTheDocument();
    expect(screen.getByText("Faqat ko‘rish rejimi")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vakolatni berish" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Bekor qilish" })).not.toBeInTheDocument();
  });

  it("lets ADMIN search directory users and grant a role while disabling self-revoke", async () => {
    api.fetchStaffGrants.mockResolvedValue(grantsPayload());
    api.fetchDirectoryUsers.mockResolvedValue([
      {
        id: CANDIDATE_ID,
        display_name: "Jasur Toshmatov",
        status: "ACTIVE",
        masked_contact: "+998 93 *** 44 55",
        mfa_enabled: true,
        platform_roles: [],
      },
    ]);
    api.grantStaffRole.mockResolvedValue({
      ok: true,
      grant_id: "g-new",
      user_id: CANDIDATE_ID,
      role_code: "COMPLIANCE",
      expires_at: "2036-11-17T00:00:00Z",
    });

    render(<StaffRolesPanel currentUserId={ADMIN_ID} roles={["CANDIDATE", "ADMIN"]} />);

    const selfCard = (await screen.findByText("Dilmurod Admin")).closest("li")!;
    expect(within(selfCard).getByRole("button", { name: "Bekor qilish" })).toBeDisabled();

    const userPickBtn = await screen.findByRole("button", { name: /Jasur Toshmatov/ });
    fireEvent.click(userPickBtn);
    fireEvent.change(screen.getByLabelText("Beriladigan rol"), { target: { value: "COMPLIANCE" } });
    fireEvent.change(screen.getByLabelText(/Tayinlash asosi/), {
      target: { value: "Komplayens va vorislik nazorati uchun tayinlandi" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Vakolatni berish" }));

    await waitFor(() =>
      expect(api.grantStaffRole).toHaveBeenCalledWith({
        user_id: CANDIDATE_ID,
        role_code: "COMPLIANCE",
        reason: "Komplayens va vorislik nazorati uchun tayinlandi",
        duration_days: 3650,
      })
    );
    expect(await screen.findByRole("status")).toHaveTextContent(/Jasur Toshmatov/);
  });

  it("opens revoke modal for another grant and calls revokeStaffRole", async () => {
    api.fetchStaffGrants.mockResolvedValue(grantsPayload());
    api.fetchDirectoryUsers.mockResolvedValue([]);
    api.revokeStaffRole.mockResolvedValue({ ok: true });

    render(<StaffRolesPanel currentUserId={ADMIN_ID} roles={["ADMIN"]} />);
    const otherCard = (await screen.findByText("Aziza Karimova")).closest("li")!;
    fireEvent.click(within(otherCard).getByRole("button", { name: "Bekor qilish" }));

    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(/Bekor qilish sababi/), {
      target: { value: "Bo‘lim rotatsiyasi munosabati bilan bekor qilindi" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Tasdiqlash va bekor qilish" }));

    await waitFor(() =>
      expect(api.revokeStaffRole).toHaveBeenCalledWith(
        "g-mod",
        "Bo‘lim rotatsiyasi munosabati bilan bekor qilindi"
      )
    );
  });
});
