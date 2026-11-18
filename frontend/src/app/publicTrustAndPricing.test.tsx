import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Suspense, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuthMeCache, type Opportunity } from "@/lib/api";
import { safeExternalWebsiteUrl } from "@/lib/publicCatalog";
import VacancyCard from "@/components/public/VacancyCard";
import PublicOrganizationPage from "./tashkilot/[id]/page";
import PublicServicesAndTariffsPage from "./tariflar/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/tariflar",
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

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

const ORG_UUID = "11111111-1111-4111-8111-111111111111";

const SAMPLE_JOB: Opportunity = {
  id: "22222222-2222-4222-8222-222222222222",
  organization_id: ORG_UUID,
  organization_name: "Toshkent Texnopark",
  organization_region: "Toshkent",
  title: "Backend muhandis yordamchisi",
  description: "Python va FastAPI bo‘yicha yarim stavka amaliyot.",
  region: "Toshkent",
  kind: "PART_TIME",
  work_mode: "HYBRID",
  contract_type: "FIXED_TERM",
  is_paid: true,
  salary_min: 3000000,
  salary_max: 4500000,
  currency: "UZS",
  schedule_policy: "Haftada 20 soat",
  capacity: 4,
  occupied_count: 1,
  vacancies_available: 3,
  published_at: "2026-11-15T10:00:00Z",
  expires_at: null,
};

describe("Public trust, organization showcase & tariffs", () => {
  beforeEach(() => {
    clearAuthMeCache();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sanitizes organization website URLs against unsafe schemes", () => {
    expect(safeExternalWebsiteUrl("https://flexbridge.uz")).toBe("https://flexbridge.uz/");
    expect(safeExternalWebsiteUrl("texnopark.uz")).toBe("https://texnopark.uz/");
    expect(safeExternalWebsiteUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalWebsiteUrl("data:text/html,hi")).toBeNull();
  });

  it("links organization name on VacancyCard to /tashkilot/[id]", () => {
    render(<VacancyCard job={SAMPLE_JOB} />);
    const orgLink = screen.getByRole("link", { name: "Toshkent Texnopark" });
    expect(orgLink).toHaveAttribute("href", `/tashkilot/${ORG_UUID}`);
    const detailLink = screen.getByRole("link", { name: "Batafsil" });
    expect(detailLink).toHaveAttribute("href", `/ishlar/${SAMPLE_JOB.id}`);
  });

  it("renders public services and 30-day pricing plans from API-011 & API-012", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/bff/public/services") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              contract_id: "API-011",
              currency: "UZS",
              updated_at: "2026-11-11T00:00:00Z",
              services: [
                {
                  code: "ACADEMIC_INTERNSHIP",
                  name_uz: "Uch tomonlama akademik amaliyot",
                  target_audience: "Talabalar va OTMlar",
                  is_active: true,
                  stage: 1,
                  description: "Raqamli kundalik va kafedra tasdig‘i.",
                  conditions: ["OTM buyrug‘i"],
                },
                {
                  code: "FREELANCE_MARKETPLACE",
                  name_uz: "Frilans buyurtmalar bozori",
                  target_audience: "Mutaxassislar",
                  is_active: false,
                  stage: 2,
                  description: "Escrow himoyali loyihalar.",
                  conditions: ["2-bosqichda joriy qilinadi"],
                },
              ],
            }),
            { status: 200 }
          )
        );
      }
      if (url === "/api/bff/public/prices") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              contract_id: "API-012",
              currency: "UZS",
              pricing_model: "SUBSCRIPTION_AND_LISTING",
              plans: [
                {
                  tier: "SINGLE_POST_30D",
                  title: "Bitta e’lon uchun 30 kunlik tarif",
                  plan_code: "SINGLE_POST_30D",
                  price_uzs: 149000,
                  duration_days: 30,
                  description: "Bitta faol e’lon.",
                  opportunity_slots: 1,
                },
              ],
              activation_rules: { speed: "INSTANT", provider: "ONLINE_GATEWAY", currency: "UZS" },
              refund_policy: {
                policy: "PRORATED_BEFORE_FIRST_APPLICATION",
                full_refund_window_hours: 24,
                description: "24 soat ichida 100% qaytariladi.",
                circuit_breaker_guarantee: true,
              },
            }),
            { status: 200 }
          )
        );
      }
      return Promise.resolve(new Response("{}", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PublicServicesAndTariffsPage />);

    expect(
      await screen.findByText(/FlexBridge Xizmatlar Katalogi & Shaffof Tariflar/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Bitta e’lon uchun 30 kunlik tarif/i)).toBeInTheDocument();
    expect(screen.getByText(/149\s*000 UZS/i)).toBeInTheDocument();
    expect(screen.getByText(/To‘lovni qaytarish kafolati \(24 soat\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Uch tomonlama akademik amaliyot/i)).toBeInTheDocument();
    expect(screen.getByText(/2-bosqich \(kelgusi\)/i)).toBeInTheDocument();
  });

  it("renders public org showcase and submits moderation abuse report when signed in", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === `/api/bff/organizations/${ORG_UUID}/public`) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              contract_id: "API-008",
              id: ORG_UUID,
              public_name: "Toshkent Texnopark",
              region: "Toshkent",
              description: "Innovatsion texnologiya markazi.",
              website: "https://texnopark.uz",
              capabilities: ["JOB_EMPLOYER", "INTERNSHIP_HOST"],
            }),
            { status: 200 }
          )
        );
      }
      if (url.startsWith(`/api/bff/organizations/${ORG_UUID}/opportunities`)) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              contract_id: "API-009",
              organization_id: ORG_UUID,
              items: [
                {
                  id: SAMPLE_JOB.id,
                  title: SAMPLE_JOB.title,
                  kind: "PART_TIME",
                  work_mode: "HYBRID",
                  location: "Toshkent",
                  capacity: 4,
                  occupied_count: 1,
                  vacancies_available: 3,
                  status: "PUBLISHED",
                  created_at: "2026-11-15T10:00:00Z",
                },
              ],
              limit: 12,
              has_more: false,
              next_cursor: null,
            }),
            { status: 200 }
          )
        );
      }
      if (url === `/api/bff/organizations/${ORG_UUID}/rating-summary`) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              contract_id: "API-010",
              target_org_id: ORG_UUID,
              score: null,
              score_status: "WITHHELD_INSUFFICIENT_SAMPLE",
              sample_size: 2,
              feature_flag: "ratings",
              feature_enabled: false,
              computed_at: null,
            }),
            { status: 200 }
          )
        );
      }
      if (url === "/api/auth/me") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              user: { user_id: "u1", session_id: "s1", roles: ["STUDENT"], display_name: "Ali" },
            }),
            { status: 200 }
          )
        );
      }
      if (url === "/api/bff/moderation-cases" && init?.method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              ok: true,
              id: "case-99",
              status: "PENDING",
              severity: "HIGH",
              category: "MISLEADING_TERMS",
            }),
            { status: 201 }
          )
        );
      }
      return Promise.resolve(new Response("{}", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const paramsPromise = Promise.resolve({ id: ORG_UUID });
    await act(async () => {
      render(
        <Suspense fallback={null}>
          <PublicOrganizationPage params={paramsPromise} />
        </Suspense>
      );
    });

    expect(await screen.findByRole("heading", { name: "Toshkent Texnopark" })).toBeInTheDocument();
    expect(screen.getByText(/Backend muhandis yordamchisi/i)).toBeInTheDocument();
    expect(screen.getByText(/Kamida 5 ta baho to‘plangach ochiladi/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Tashkilot ustidan shikoyat/i }));
    expect(await screen.findByText(/Moderatsiyaga shikoyat yuborish/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Muhimlik darajasi/i), { target: { value: "HIGH" } });
    fireEvent.change(screen.getByLabelText(/Batafsil izoh/i), {
      target: { value: "Vakansiyadagi ish haqi suhbatda boshqacha aytildi." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Moderatsiyaga yuborish/i }));

    await waitFor(() => {
      expect(screen.getByText(/Murojaatingiz qabul qilindi/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/case-99/i)).toBeInTheDocument();
  });
});
