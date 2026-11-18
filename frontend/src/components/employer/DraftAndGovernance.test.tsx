import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DraftOpportunityEditorModal from "./DraftOpportunityEditorModal";
import OwnerGovernancePanel from "./OwnerGovernancePanel";

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

const ORG_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const OPP_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const CONT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const CONTACT_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";

describe("Employer draft editor & ownership governance", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads draft vacancy detail and saves core metadata, terms, and shifts", async () => {
    const calls: Array<{ url: string; method: string; body?: unknown }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ url, method, body });

      if (url === `/api/bff/opportunities/${OPP_ID}`) {
        return new Response(
          JSON.stringify({
            contract_id: "API-005",
            id: OPP_ID,
            organization_id: ORG_ID,
            kind: "INTERNSHIP",
            status: "DRAFT",
            capacity: 3,
            occupied_count: 0,
            vacancies_available: 0,
            published_at: null,
            expires_at: null,
            closed_at: null,
            revision: {
              title: "QA amaliyotchi",
              description: "Dastlabki tavsif matni.",
              region: "Toshkent shahri",
              work_mode: "HYBRID",
              eligibility: "STUDENTS_ONLY",
              contract_type: "INTERNSHIP_AGREEMENT",
              is_paid: true,
              salary_min: 1500000,
              salary_max: 2000000,
              currency: "UZS",
              salary_period: "MONTH",
              salary_basis: "GROSS",
              schedule_policy: "STRICT",
            },
            organization: { id: ORG_ID, name: "Artel LLC", status: "VERIFIED" },
            skills: [],
            shifts: [
              { id: "sh-1", group_code: "GROUP_A", weekday: 1, start_minute: 540, end_minute: 780, is_required: true },
            ],
          }),
          { status: 200 }
        );
      }

      if (url.startsWith(`/api/bff/employer/opportunities/${OPP_ID}/draft`)) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSaved = vi.fn();
    render(
      <DraftOpportunityEditorModal
        isOpen
        opportunityId={OPP_ID}
        onClose={vi.fn()}
        onSaved={onSaved}
      />
    );

    const titleInput = (await screen.findByLabelText(/Lavozim \/ Amaliyot sarlavhasi/i)) as HTMLInputElement;
    expect(titleInput.value).toBe("QA amaliyotchi");

    fireEvent.change(titleInput, { target: { value: "Senior QA amaliyotchi" } });
    fireEvent.click(screen.getByRole("button", { name: /Asosiy qismni saqlash/i }));

    await waitFor(() => {
      expect(screen.getByText(/Asosiy qoralama ma’lumotlari saqlandi/i)).toBeInTheDocument();
    });
    expect(onSaved).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /To‘lov va muddat/i }));
    fireEvent.change(screen.getByLabelText(/Minimal maosh/i), { target: { value: "2500000" } });
    fireEvent.click(screen.getByRole("button", { name: /To‘lov shartlarini saqlash/i }));
    await waitFor(() => {
      expect(screen.getByText(/To‘lov va muddat shartlari yangilandi/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Smenalar jadvali/i }));
    fireEvent.click(screen.getByRole("button", { name: /Smenalarni saqlash/i }));
    await waitFor(() => {
      expect(screen.getByText(/Haftalik smena va jadval tartibi yangilandi/i)).toBeInTheDocument();
    });

    expect(calls.some((c) => c.url.endsWith("/draft") && c.method === "PUT")).toBe(true);
    expect(calls.some((c) => c.url.endsWith("/draft/terms") && c.method === "PUT")).toBe(true);
    expect(calls.some((c) => c.url.endsWith("/draft/schedule") && c.method === "PUT")).toBe(true);
  });

  it("renders owner continuity objections and incoming co-owner consent inbox with MFA active", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url === "/api/bff/me/security") {
        return new Response(
          JSON.stringify({
            ok: true,
            totp_enabled: true,
            sessions: [{ id: "s1", is_current: true, assurance: "MFA" }],
          }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/employer/organization/${ORG_ID}/team`) {
        return new Response(
          JSON.stringify({
            organization: {
              id: ORG_ID,
              public_name: "Artel LLC",
              legal_name: "Artel MChJ",
              status: "VERIFIED",
              tax_id: "123456789",
              region: "Toshkent",
            },
            members: [
              { membership_id: "m-owner", display_name: "Akmal Owner", status: "ACTIVE", roles: ["OWNER"], is_self: true, created_at: "2026-11-01T00:00:00Z", accepted_at: "2026-11-01T00:00:00Z", revoked_at: null },
              { membership_id: "m-hr", display_name: "Dilnoza HR", status: "ACTIVE", roles: ["HR"], is_self: false, created_at: "2026-11-01T00:00:00Z", accepted_at: "2026-11-01T00:00:00Z", revoked_at: null },
            ],
            join_requests: [],
            invitations: [],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/contacts") {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ id: CONTACT_ID, channel: "PHONE", masked_destination: "+99890***0011", verified_at: "2026-11-01T00:00:00Z" }],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/owner-requests") {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ case_id: "case-req-1", organization_id: ORG_ID, public_name: "Partner LLC", status: "WAITING_CONSENT", current_revision: 1, created_at: "2026-11-18T00:00:00Z" }],
          }),
          { status: 200 }
        );
      }
      if (url === "/api/bff/me/owner-transfers") {
        return new Response(JSON.stringify({ ok: true, items: [] }), { status: 200 });
      }
      if (url === `/api/bff/employer/organization/${ORG_ID}/owner-continuity` && (!init?.method || init.method === "GET")) {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ id: CONT_ID, status: "WAITING_MODERATOR", created_at: "2026-11-18T00:00:00Z", applicant_id: "u-hr", applicant_display_name: "Dilnoza HR" }],
          }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/employer/organization/${ORG_ID}/owner-continuity/${CONT_ID}/object`) {
        return new Response(JSON.stringify({ ok: true, id: CONT_ID, status: "CANCELLED" }), { status: 200 });
      }
      if (url === "/api/bff/me/owner-requests/case-req-1/consent") {
        return new Response(JSON.stringify({ ok: true, id: "case-req-1", status: "PENDING" }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<OwnerGovernancePanel orgId={ORG_ID} />);

    expect(await screen.findByText(/Vorislik \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Mening roziligim \(1\)/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Vorislik \(1\)/i }));
    expect(await screen.findByText(/Arizachi: Dilnoza HR/i)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/E’tiroz sababi/i), {
      target: { value: "Men faol rahbar sifatida ishlayapman." },
    });
    fireEvent.click(screen.getByRole("button", { name: /E’tiroz bildirish/i }));
    await waitFor(() => {
      expect(screen.getByText(/Vorislik so‘roviga rasmiy e’tiroz kiritildi/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Mening roziligim \(1\)/i }));
    expect(await screen.findByText(/Partner LLC — Hamrahbar \(OWNER\) taklifi/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Rozilik beraman/i }));
    await waitFor(() => {
      expect(screen.getByText(/Rozilik yuborildi/i)).toBeInTheDocument();
    });
  });
});
