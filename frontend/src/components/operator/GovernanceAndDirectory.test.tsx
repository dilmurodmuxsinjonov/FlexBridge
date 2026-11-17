import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchDirectoryUsers: vi.fn(),
  fetchDirectoryOrganizations: vi.fn(),
  fetchDirectoryInstitutions: vi.fn(),
  fetchPrivacyRequests: vi.fn(),
  resolvePrivacyRequest: vi.fn(),
  fetchRecoveryRequests: vi.fn(),
  decideRecoveryRequest: vi.fn(),
  fetchModerationAppeals: vi.fn(),
  fetchOwnerContinuityCases: vi.fn(),
  fetchPilotReadiness: vi.fn(),
  evaluateRetentionDryRun: vi.fn(),
}));

vi.mock("@/lib/platformAdmin", async (orig) => ({
  ...(await orig<typeof import("@/lib/platformAdmin")>()),
  ...api,
}));

import DirectoryPanel from "./DirectoryPanel";
import GovernanceOpsPanel from "./GovernanceOpsPanel";

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset());
});

describe("DirectoryPanel", () => {
  it("hides user search for MODERATOR and defaults cleanly to organizations", async () => {
    api.fetchDirectoryOrganizations.mockResolvedValue([
      {
        id: "org-1",
        public_name: "Uzum Tech",
        legal_name: "Uzum Tech MCHJ",
        tax_id: "305000001",
        region: "Toshkent",
        verification_status: "VERIFIED",
        active_members_count: 5,
        published_opportunities_count: 3,
      },
    ]);

    render(<DirectoryPanel roles={["MODERATOR"]} />);

    expect(await screen.findByText("Uzum Tech")).toBeInTheDocument();
    expect(api.fetchDirectoryUsers).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Foydalanuvchilar" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Korxonalar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OTM / Universitetlar" })).toBeInTheDocument();
  });
});

describe("GovernanceOpsPanel", () => {
  it("lets SUPPORT review and approve a recovery request", async () => {
    api.fetchPrivacyRequests.mockResolvedValue([]);
    api.fetchRecoveryRequests.mockResolvedValue([
      {
        id: "rec-1",
        user_id: "u-1",
        display_name: "Madina Rustamova",
        status: "PENDING_REVIEW",
        masked_contacts: [{ channel: "PHONE", masked: "+998 90 *** 11 22" }],
        created_at: "2026-11-17T08:00:00Z",
      },
    ]);
    api.decideRecoveryRequest.mockResolvedValue({
      ok: true,
      id: "rec-1",
      status: "APPROVED",
      valid_until: "2026-11-20T08:00:00Z",
    });

    render(<GovernanceOpsPanel roles={["SUPPORT"]} initialSection="RECOVERY" />);

    expect(await screen.findByText("Madina Rustamova")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ko‘rib chiqish" }));

    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(/Qaror asosi/), {
      target: { value: "Telefon va shaxsiy hujjat operator tomonidan tasdiqlandi" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Qarorni yuborish" }));

    await waitFor(() =>
      expect(api.decideRecoveryRequest).toHaveBeenCalledWith("rec-1", {
        decision: "APPROVE",
        reason: "Telefon va shaxsiy hujjat operator tomonidan tasdiqlandi",
      })
    );
    expect(await screen.findByRole("status")).toHaveTextContent(/72 soat amal qiladi/);
  });

  it("lets COMPLIANCE view pilot readiness and submit retention dry-run", async () => {
    api.fetchPilotReadiness.mockResolvedValue({
      pilot_ready: false,
      acceptance_status: "REQUIRES_E2E_AND_DR_EVIDENCE",
      schema_migrated: true,
      finance_circuit_state: "CLOSED",
      release_stage: "R1_IMPLEMENTATION",
      r2_freelance_enabled: false,
      feature_flag_read_status: "AVAILABLE",
      disaster_recovery_targets: { rpo_hours: 24, rto_hours: 4, restore_drill_verified: false },
    });
    api.evaluateRetentionDryRun.mockResolvedValue({
      id: "ret-1",
      data_category: "OTP_CHALLENGE_DIGEST",
      age_days: 30,
      mode: "DRY_RUN",
      status: "EVALUATED_ONLY",
      records_scanned: 0,
      records_actioned: 0,
      evaluation: { outcome: "PURGE_DUE" },
    });

    render(<GovernanceOpsPanel roles={["COMPLIANCE"]} initialSection="OPERATIONS" />);

    expect(await screen.findByText("O‘chirilgan (R1 qoidasi)")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xavfsiz bahoni yozish (Dry-run)" }));

    await waitFor(() =>
      expect(api.evaluateRetentionDryRun).toHaveBeenCalledWith({
        data_category: "OTP_CHALLENGE_DIGEST",
        age_days: 30,
      })
    );
    expect(await screen.findByText(/Tozalash muddati yetgan/)).toBeInTheDocument();
  });
});
