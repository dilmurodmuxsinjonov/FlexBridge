import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchFeatureFlags: vi.fn(),
  patchFeatureFlag: vi.fn(),
}));

vi.mock("@/lib/platformAdmin", async (orig) => ({
  ...(await orig<typeof import("@/lib/platformAdmin")>()),
  ...api,
}));

import FeatureFlagsPanel from "./FeatureFlagsPanel";

const sampleFlags = [
  {
    code: "R1_PART_TIME_JOBS",
    category: "R1" as const,
    enabled: false,
    version: 3,
    mutable: true,
    disable_only: false,
    reason: "Boshlang‘ich holat",
    alias_of: null,
  },
  {
    code: "ratings",
    category: "PROTECTED" as const,
    enabled: false,
    version: 0,
    mutable: false,
    disable_only: true,
    reason: "R1 himoyalangan flag",
    alias_of: null,
  },
  {
    code: "R2_FREELANCE_MARKETPLACE",
    category: "R2" as const,
    enabled: false,
    version: 0,
    mutable: false,
    disable_only: true,
    reason: "Keyingi bosqich",
    alias_of: null,
  },
  {
    code: "R1_PAID_ORG_PLANS",
    category: "PROTECTED" as const,
    enabled: false,
    version: 0,
    mutable: false,
    disable_only: false,
    reason: "Taxallus",
    alias_of: "paid_checkout",
  },
];

beforeEach(() => {
  api.fetchFeatureFlags.mockReset();
  api.patchFeatureFlag.mockReset();
});

describe("FeatureFlagsPanel", () => {
  it("keeps protected, R2, and alias flags safety-locked while letting ADMIN toggle R1 flags", async () => {
    api.fetchFeatureFlags.mockResolvedValue(sampleFlags);
    api.patchFeatureFlag.mockResolvedValue({
      ok: true,
      code: "R1_PART_TIME_JOBS",
      enabled: true,
      version: 4,
    });

    render(<FeatureFlagsPanel roles={["ADMIN"]} />);

    expect(await screen.findByText("Yarim stavka ish e’lonlari")).toBeInTheDocument();

    const ratingsCard = screen.getByText("Reyting va baholash tizimi").closest("li")!;
    expect(within(ratingsCard).queryByRole("button")).not.toBeInTheDocument();
    expect(within(ratingsCard).getByText(/Xavfsizlik qulflangan/)).toBeInTheDocument();

    const r2Card = screen.getByText("Frilans bozori (R2 bosqich)").closest("li")!;
    expect(within(r2Card).queryByRole("button")).not.toBeInTheDocument();

    const aliasCard = screen.getByText("Korxona pullik tariflari (taxallus)").closest("li")!;
    expect(within(aliasCard).getByText(/faqat o‘qish/)).toBeInTheDocument();

    const r1Card = screen.getByText("Yarim stavka ish e’lonlari").closest("li")!;
    fireEvent.click(within(r1Card).getByRole("button", { name: "Yoqish" }));

    const dialog = await screen.findByRole("dialog");
    const submitBtn = within(dialog).getByRole("button", { name: "Tasdiqlash" });
    expect(submitBtn).toBeDisabled();

    fireEvent.change(within(dialog).getByLabelText(/O‘zgartirish asosi/), {
      target: { value: "Pilot korxonalar uchun yarim stavka e’lonlar yoqildi" },
    });
    expect(submitBtn).toBeEnabled();
    fireEvent.click(submitBtn);

    await waitFor(() =>
      expect(api.patchFeatureFlag).toHaveBeenCalledWith("R1_PART_TIME_JOBS", {
        enabled: true,
        reason: "Pilot korxonalar uchun yarim stavka e’lonlar yoqildi",
        expectedVersion: 3,
      })
    );
    expect(await screen.findByRole("status")).toHaveTextContent(/versiya 4/);
  });

  it("shows read-only view for AUDITOR and OPERATIONS without edit buttons", async () => {
    api.fetchFeatureFlags.mockResolvedValue(sampleFlags);
    render(<FeatureFlagsPanel roles={["AUDITOR", "OPERATIONS"]} />);

    expect(await screen.findByText("Yarim stavka ish e’lonlari")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Yoqish" })).not.toBeInTheDocument();
    expect(screen.getByText(/Sizning rolingiz faqat holatni ko‘ra oladi/)).toBeInTheDocument();
    expect(screen.getAllByText(/Faqat Bosh administrator o‘zgartiradi/)).toHaveLength(4);
  });
});
