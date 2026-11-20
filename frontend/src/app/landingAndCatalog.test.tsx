import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuthMeCache, type Opportunity } from "@/lib/api";
import { ThemeProvider } from "@/components/ThemeProvider";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import LandingPage from "./page";
import PublicCatalogPage from "./elonlar/page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
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

const SAMPLE_JOBS: Opportunity[] = [
  {
    id: "job-1",
    organization_id: "org-1",
    organization_name: "O‘zbekiston FinTech Markazi",
    organization_region: "Toshkent",
    title: "Frontend amaliyotchi (React)",
    description: "Darsdan bo‘sh vaqtda amaliyot o‘tash imkoniyati.",
    region: "Toshkent",
    kind: "INTERNSHIP",
    work_mode: "HYBRID",
    contract_type: "INTERNSHIP",
    is_paid: true,
    salary_min: 2500000,
    salary_max: 4000000,
    currency: "UZS",
    schedule_policy: "Kuniga 4 soat, gibrid",
    capacity: 5,
    occupied_count: 1,
    vacancies_available: 4,
    published_at: "2026-11-15T10:00:00Z",
    expires_at: null,
  },
  {
    id: "job-2",
    organization_id: "org-2",
    organization_name: "Samarqand Raqamli Texnopark",
    organization_region: "Samarqand",
    title: "Ma’lumotlar tahlilchisi yordamchisi",
    description: null,
    region: "Samarqand",
    kind: "PART_TIME",
    work_mode: "ONSITE",
    contract_type: "FIXED_TERM",
    is_paid: false,
    salary_min: null,
    salary_max: null,
    currency: "UZS",
    schedule_policy: null,
    capacity: 3,
    occupied_count: 1,
    vacancies_available: 2,
    published_at: "2026-11-14T10:00:00Z",
    expires_at: null,
  },
];

function mockApi(options: { user?: { user_id: string; session_id: string; roles: string[]; display_name?: string } | null; jobs?: Opportunity[]; failJobs?: boolean } = {}) {
  const { user = null, jobs = SAMPLE_JOBS, failJobs = false } = options;
  return vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.startsWith("/api/auth/me")) {
      return Promise.resolve(
        new Response(JSON.stringify(user ? { ok: true, user } : { ok: false }), {
          status: user ? 200 : 401,
          headers: { "Content-Type": "application/json" },
        })
      );
    }
    if (url.startsWith("/api/backend/opportunities")) {
      if (failJobs) {
        return Promise.resolve(new Response("error", { status: 500 }));
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            contract_id: "API-001",
            items: jobs,
            has_more: false,
            next_after: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      );
    }
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

describe("Pre-Auth Bosh Sahifa (/) and Public Catalog (/elonlar)", () => {
  beforeEach(() => {
    clearAuthMeCache();
  });

  afterEach(() => {
    clearAuthMeCache();
  });

  it("renders pre-auth Bosh Sahifa with hero CTAs, all 4 role portal links, capabilities, and featured vacancies", async () => {
    const fetchMock = mockApi();
    vi.stubGlobal("fetch", fetchMock);

    render(<LandingPage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /Talabalar amaliyoti, smenali ish va OTM nazorati/i,
      })
    ).toBeInTheDocument();

    const html = document.body.innerHTML;
    for (const expectedHref of [
      "/royxatdan-otish",
      "/kirish",
      "/elonlar",
      "/talaba/kirish",
      "/nomzod",
      "/korxona/kirish",
      "/employer",
      "/universitet/kirish",
      "/university",
      "/operator/kirish",
      "/operator",
      "/haqida",
      "/shartlar",
      "/maxfiylik",
    ]) {
      expect(html).toContain(`href="${expectedHref}"`);
    }

    expect(html).not.toContain("Verified Skill");
    expect(html).not.toContain("Match Coach");
    expect(html).not.toContain("SOC");

    await waitFor(() => {
      expect(screen.getByText("Frontend amaliyotchi (React)")).toBeInTheDocument();
    });
    expect(document.body.innerHTML).toContain('href="/ishlar/job-1"');
  });

  it("shows quick dashboard jump banner on / when signed in", async () => {
    vi.stubGlobal(
      "fetch",
      mockApi({
        user: {
          user_id: "u-1",
          session_id: "s-1",
          roles: ["CANDIDATE"],
          display_name: "Dilmurod",
        },
      })
    );

    render(<LandingPage />);

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /Kabinetimga o‘tish/i })).toHaveAttribute(
        "href",
        "/nomzod"
      );
    });
  });

  it("renders standalone /elonlar catalog with search, balance telemetry, vacancy cards, and error retry", async () => {
    const fetchMock = mockApi({ failJobs: true });
    vi.stubGlobal("fetch", fetchMock);

    render(<PublicCatalogPage />);

    await waitFor(() => {
      expect(screen.getByText("E’lonlarni yuklab bo‘lmadi")).toBeInTheDocument();
    });

    fetchMock.mockImplementation(mockApi({ jobs: SAMPLE_JOBS }));
    fireEvent.click(screen.getByRole("button", { name: /Qayta urinish/i }));

    await waitFor(() => {
      expect(screen.getByText("Frontend amaliyotchi (React)")).toBeInTheDocument();
      expect(screen.getByText("Ma’lumotlar tahlilchisi yordamchisi")).toBeInTheDocument();
    });
    expect(screen.getByText("Katalog balansi")).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /Faqat to‘lovli e’lonlar/i })).toBeInTheDocument();

    // Selecting a region or payment filter in <select> applies immediately without requiring an extra submit click
    fireEvent.change(screen.getByLabelText("Hudud"), { target: { value: "Toshkent" } });
    await waitFor(() => {
      const regionCalls = fetchMock.mock.calls.filter(([url]) =>
        String(url).includes("region=Toshkent")
      );
      expect(regionCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("deduplicates /api/auth/me across Navbar, Footer, and LandingPage into one request and includes Bosh sahifa + E’lonlar in public nav", async () => {
    const fetchMock = mockApi();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <ThemeProvider>
        <Navbar />
        <LandingPage />
        <Footer />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Frontend amaliyotchi (React)")).toBeInTheDocument();
    });

    const authMeCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).startsWith("/api/auth/me")
    );
    expect(authMeCalls).toHaveLength(1);

    const navHtml = document.body.innerHTML;
    expect(navHtml).toContain("Bosh sahifa");
    expect(navHtml).toContain('href="/elonlar"');
  });
});
