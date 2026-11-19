import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PaymentsPage from "./page";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    prefetch: _prefetch,
    ...rest
  }: {
    href: string;
    children: ReactNode;
    prefetch?: boolean;
    [key: string]: unknown;
  }) => {
    void _prefetch;
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    );
  },
}));

const mockFetchPublicPrices = vi.fn();
vi.mock("@/lib/publicCatalog", () => ({
  fetchPublicPrices: (...args: unknown[]) => mockFetchPublicPrices(...args),
}));

const mockFetchAuthMe = vi.fn();
const mockFetchMyWorkspaces = vi.fn();
const mockFetchOrgBillingOverview = vi.fn();
const mockFetchOrgEntitlements = vi.fn();
const mockCreateOrgOrder = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchAuthMe: (...args: unknown[]) => mockFetchAuthMe(...args),
    fetchMyWorkspaces: (...args: unknown[]) => mockFetchMyWorkspaces(...args),
    fetchOrgBillingOverview: (...args: unknown[]) => mockFetchOrgBillingOverview(...args),
    fetchOrgEntitlements: (...args: unknown[]) => mockFetchOrgEntitlements(...args),
    createOrgOrder: (...args: unknown[]) => mockCreateOrgOrder(...args),
  };
});

const SAMPLE_PRICES = {
  contract_id: "API-012",
  currency: "UZS",
  pricing_model: "SUBSCRIPTION_AND_LISTING",
  plans: [
    {
      tier: "PILOT_FREE",
      title: "Pilot sinov tarifi",
      plan_code: "PILOT_FREE",
      price_uzs: 0,
      duration_days: 30,
      description: "Akademik hamkorlar uchun dastlabki bepul e'lonlar.",
      opportunity_slots: 5,
    },
    {
      tier: "SINGLE_POST_30D",
      title: "Bitta e'lon uchun 30 kunlik tarif",
      plan_code: "SINGLE_POST_30D",
      price_uzs: 149000,
      duration_days: 30,
      description: "Bitta e'lonni 30 kun faol saqlash.",
      opportunity_slots: 1,
    },
    {
      tier: "ORG_PLAN_30D",
      title: "Tashkilot uchun 30 kunlik obuna",
      plan_code: "ORG_PLAN_30D",
      price_uzs: 599000,
      duration_days: 30,
      description: "Bir vaqtda 5 tagacha faol e'lon.",
      opportunity_slots: 5,
    },
  ],
  activation_rules: {
    speed: "IMMEDIATE_ON_WEBHOOK_CONFIRMATION",
    provider: "UZS_PAYMENT_ADAPTER",
    currency: "UZS",
  },
  refund_policy: {
    policy: "FULL_REFUND_WINDOW",
    full_refund_window_hours: 24,
    description: "To‘lov tasdiqlangandan keyin 24 soat ichida to‘liq qaytarish so‘rash mumkin.",
    circuit_breaker_guarantee: true,
  },
};

describe("PaymentsPage (/tolovlar)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, "", "/tolovlar");
    mockFetchPublicPrices.mockResolvedValue(SAMPLE_PRICES);
  });

  it("renders guest preview with disconnected gateway notice, providers, and disabled live-pay button", async () => {
    mockFetchAuthMe.mockResolvedValue(null);

    render(<PaymentsPage />);

    expect(await screen.findByText("Onlayn to‘lov sahifasi")).toBeInTheDocument();
    expect(screen.getByText(/To‘lov shlyuzi hozircha ulanmagan/i)).toBeInTheDocument();
    expect(screen.getAllByText(/599[\s\u00a0]000 UZS/).length).toBeGreaterThan(0);

    expect(screen.getByRole("radio", { name: /Click/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Payme/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Uzum Bank/i })).toBeInTheDocument();

    const payButton = screen.getByRole("button", { name: /Onlayn to‘lash — provayder ulanmagan/i });
    expect(payButton).toBeDisabled();

    expect(screen.getByRole("link", { name: /Buyurtma berish uchun korxona kirishi/i })).toHaveAttribute(
      "href",
      "/korxona/kirish?redirect=/tolovlar"
    );
  });

  it("allows authenticated employer OWNER to preview plans/providers and create a PENDING_PAYMENT order", async () => {
    mockFetchAuthMe.mockResolvedValue({
      user_id: "user-1",
      session_id: "sess-1",
      roles: ["EMPLOYER"],
      display_name: "Demo Employer",
    });
    mockFetchMyWorkspaces.mockResolvedValue({
      organizations: [
        {
          id: "org-1",
          name: "Artel Tech",
          region: "Toshkent",
          status: "VERIFIED",
          roles: ["OWNER"],
        },
      ],
      institutions: [],
    });
    mockFetchOrgBillingOverview.mockResolvedValue({
      ok: true,
      contract_id: "API-093",
      organization_id: "org-1",
      plan: {
        code: "PILOT_FREE",
        status: "ACTIVE",
        starts_at: null,
        ends_at: null,
        quota: 20,
        concurrent_active_limit: 20,
      },
      orders: [
        {
          id: "ord-existing-1234",
          amount: 599000,
          currency: "UZS",
          status: "PENDING_PAYMENT",
          plan_code: "ORG_PLAN_30D",
          created_at: "2026-11-19T10:00:00Z",
        },
      ],
      invoices: [],
    });
    mockFetchOrgEntitlements.mockResolvedValue({
      ok: true,
      contract_id: "API-070",
      organization_id: "org-1",
      has_active_entitlement: true,
      active_entitlement: null,
      usage: {
        concurrent_active_opportunities: 2,
        concurrent_active_limit: 20,
        concurrent_slots_available: 18,
        quota_remaining: 15,
        days_remaining: 29,
      },
    });
    mockCreateOrgOrder.mockResolvedValue({
      ok: true,
      contract_id: "API-094",
      order: {
        id: "ord-new-99887766",
        amount: 149000,
        currency: "UZS",
        status: "PENDING_PAYMENT",
        plan_code: "SINGLE_POST_30D",
        created_at: "2026-11-19T12:00:00Z",
      },
      invoice: {
        id: "inv-1",
        order_id: "ord-new-99887766",
        number: "INV-001",
        amount: 149000,
        currency: "UZS",
        fiscal_status: "PENDING",
        status: "ISSUED",
        issued_at: "2026-11-19T12:00:00Z",
        paid_at: null,
      },
    });

    render(<PaymentsPage />);

    expect(await screen.findByText(/#ord-exis/)).toBeInTheDocument();
    expect(screen.getByText(/18 \/ 20/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: /Bitta e'lon uchun 30 kunlik tarif/i }));
    fireEvent.click(screen.getByRole("radio", { name: /Payme/i }));

    const orderButton = screen.getByRole("button", { name: /Buyurtma yaratish \(To‘lov kutilmoqda\)/i });
    fireEvent.click(orderButton);

    await waitFor(() => {
      expect(mockCreateOrgOrder).toHaveBeenCalledWith(
        "org-1",
        expect.objectContaining({
          plan_code: "SINGLE_POST_30D",
        })
      );
    });
    expect(await screen.findByText(/Buyurtma #ord-new- yaratildi/i)).toBeInTheDocument();
  });
});
