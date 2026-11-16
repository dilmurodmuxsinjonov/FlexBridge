import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ fetchModerationQueue: vi.fn(), decideVacancy: vi.fn() }));
vi.mock("@/lib/moderation", async (orig) => ({ ...(await orig<typeof import("@/lib/moderation")>()), ...api }));

import ModerationPanel from "./ModerationPanel";

const vacancy = (over = {}) => ({
  id: "11111111-1111-4111-8111-111111111111",
  kind: "INTERNSHIP",
  capacity: 3,
  created_at: "2026-11-17T08:00:00Z",
  title: "QA stajyor",
  description: "Testlash bo‘yicha amaliyot",
  contract_type: "INTERNSHIP_AGREEMENT",
  work_mode: "HYBRID",
  region: "Toshkent",
  is_paid: true,
  salary_min: 35000,
  salary_max: null,
  salary_period: "HOUR",
  currency: "UZS",
  organization_id: "o1",
  organization_name: "Uzum Tech",
  organization_status: "VERIFIED",
  own: false,
  ...over,
});

beforeEach(() => {
  api.fetchModerationQueue.mockReset();
  api.decideVacancy.mockReset();
});

describe("ModerationPanel", () => {
  it("lists drafts with company, terms and pay in plain words", async () => {
    api.fetchModerationQueue.mockResolvedValue([vacancy()]);
    render(<ModerationPanel />);
    expect(await screen.findByText("QA stajyor")).toBeInTheDocument();
    expect(screen.getByText("Uzum Tech")).toBeInTheDocument();
    expect(screen.getByText("Amaliyot shartnomasi")).toBeInTheDocument();
    expect(screen.getByText(/35.000 UZS \/ soat/)).toBeInTheDocument();
  });

  it("requires a 15+ character note and sends the decision", async () => {
    api.fetchModerationQueue.mockResolvedValueOnce([vacancy()]).mockResolvedValue([]);
    api.decideVacancy.mockResolvedValue({ ok: true });
    render(<ModerationPanel />);
    fireEvent.click(await screen.findByRole("button", { name: /Tasdiqlash$/ }));
    const send = screen.getByRole("button", { name: "Tasdiqlashni yuborish" });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Izoh/), { target: { value: "Matn, to‘lov va shartnoma turi tekshirildi" } });
    fireEvent.click(send);
    await waitFor(() => expect(api.decideVacancy).toHaveBeenCalledWith(vacancy().id, "APPROVE", "MEETS_POLICY", "Matn, to‘lov va shartnoma turi tekshirildi"));
    expect(await screen.findByRole("status")).toHaveTextContent("«QA stajyor» tasdiqlandi");
    expect(await screen.findByText("Moderatsiya kutayotgan e’lon yo‘q")).toBeInTheDocument();
  });

  it("does not offer a decision on the moderator's own draft", async () => {
    api.fetchModerationQueue.mockResolvedValue([vacancy({ own: true })]);
    render(<ModerationPanel />);
    const item = (await screen.findByText("QA stajyor")).closest("li")!;
    expect(within(item).queryByRole("button", { name: /Tasdiqlash/ })).not.toBeInTheDocument();
    expect(within(item).getByText(/boshqa moderator ko‘rib chiqadi/)).toBeInTheDocument();
  });
});
