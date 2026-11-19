import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PlacementCompletionControls from "./PlacementCompletionControls";
import PlacementLifecycleModal from "../employer/PlacementLifecycleModal";
import TaskEvidenceDrawer from "../diary/TaskEvidenceDrawer";

const ORG_ID = "11111111-1111-4111-8111-111111111111";
const PLC_ID = "22222222-2222-4222-8222-222222222222";
const TERMS_ID = "33333333-3333-4333-8333-333333333333";
const ENTRY_ID = "44444444-4444-4444-8444-444444444444";
const FILE_ID = "55555555-5555-4555-8555-555555555555";
const MENTOR_USER_ID = "66666666-6666-4666-8666-666666666666";

describe("Phase C placement lifecycle, evidence, and mentor flows", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal("open", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("handles bilateral completion request and placement export download", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === `/api/bff/placements/${PLC_ID}/completion-requests`) {
        return new Response(JSON.stringify({ ok: true, placement_status: "COMPLETION_REQUESTED" }), { status: 200 });
      }
      if (url === `/api/bff/placements/${PLC_ID}/exports`) {
        return new Response(
          JSON.stringify({
            ok: true,
            export_id: "exp-12345678",
            placement_id: PLC_ID,
            file_id: FILE_ID,
            export_format: "PDF",
            created_at: "2026-11-18T10:00:00Z",
            expires_at: "2026-11-19T10:00:00Z",
            download_url: `/api/v1/files/${FILE_ID}/download`,
            disclaimer: "Tasdiqlangan kundaliklar jamlanmasi.",
            summary: {},
          }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/files/${FILE_ID}/download`) {
        return new Response(JSON.stringify({ ok: true, signed_url: "https://files.example.test/report.pdf" }), {
          status: 200,
        });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onUpdated = vi.fn();
    render(
      <PlacementCompletionControls
        placementId={PLC_ID}
        status="ACTIVE"
        termsId={TERMS_ID}
        version={1}
        onUpdated={onUpdated}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Yakunlashni so‘rash/i }));
    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));
    expect(calls[0].body?.decision).toBe("REQUEST_COMPLETION");

    fireEvent.click(screen.getByRole("button", { name: /PDF eksport/i }));
    await waitFor(() => expect(screen.getByText(/PDF amaliyot hisoboti tayyorlandi/i)).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: /^Yuklab olish$/i }));
    await waitFor(() =>
      expect(calls.some((c) => c.url === `/api/bff/files/${FILE_ID}/download`)).toBe(true)
    );
  });

  it("loads host plan/mentors, publishes plan edits, and runs mentor nomination + activate", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === `/api/bff/employer/placements/${PLC_ID}/plan` && method === "GET") {
        return new Response(
          JSON.stringify({
            ok: true,
            placement_id: PLC_ID,
            status: "PLANNED",
            terms_id: TERMS_ID,
            version: 1,
            start_date: "2026-11-18",
            end_date: "2026-12-18",
            academic_required: false,
            title: "Backend reja",
            objectives: "FastAPI va Postgres",
            daily_limit_minutes: 480,
            weekly_limit_minutes: 2400,
            required_minutes: 4800,
            tasks: [{ code: "T1", title: "API yozish", expected_result: "PR", required: true, target_minutes: 120 }],
          }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/employer/organization/${ORG_ID}/mentors`) {
        return new Response(
          JSON.stringify({
            ok: true,
            items: [{ user_id: MENTOR_USER_ID, membership_id: "mem-1", display_name: "Ali Valiyev" }],
          }),
          { status: 200 }
        );
      }
      if (url === `/api/bff/employer/placements/${PLC_ID}/mentor-assignments` && method === "GET") {
        return new Response(JSON.stringify({ ok: true, items: [] }), { status: 200 });
      }
      if (
        (url === `/api/bff/employer/placements/${PLC_ID}/plan` && method === "PUT") ||
        (url === `/api/bff/employer/placements/${PLC_ID}/mentor-assignments` && method === "POST") ||
        url === `/api/bff/employer/placements/${PLC_ID}/host-decisions`
      ) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onUpdated = vi.fn();
    render(
      <PlacementLifecycleModal
        isOpen
        placement={{
          id: PLC_ID,
          application_id: "app-1",
          offer_id: "off-1",
          candidate_id: "cand-1",
          organization_id: ORG_ID,
          academic_track: false,
          status: "PLANNED",
          start_date: "2026-11-18",
          end_date: "2026-12-18",
          version: 1,
          current_terms_id: TERMS_ID,
        }}
        orgId={ORG_ID}
        onClose={vi.fn()}
        onUpdated={onUpdated}
      />
    );

    await waitFor(() => expect(screen.getByDisplayValue("Backend reja")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Rejani nashr qilish/i }));
    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: /Mentor & Holat/i }));
    await waitFor(() => expect(screen.getByText("Ali Valiyev")).toBeTruthy());

    fireEvent.click(screen.getByRole("button", { name: /Mentorni biriktirish/i }));
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.url === `/api/bff/employer/placements/${PLC_ID}/mentor-assignments` &&
            c.method === "POST" &&
            c.body?.mentor_id === MENTOR_USER_ID
        )
      ).toBe(true)
    );

    fireEvent.click(screen.getByRole("button", { name: /Amaliyotni faollashtirish/i }));
    await waitFor(() =>
      expect(
        calls.some(
          (c) => c.url === `/api/bff/employer/placements/${PLC_ID}/host-decisions` && c.body?.action === "ACTIVATE"
        )
      ).toBe(true)
    );
  });

  it("uploads PDF and attaches evidence to a draft log entry (API-055)", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === `/api/bff/candidate/log-entries/${ENTRY_ID}/evidence` && method === "GET") {
        return new Response(JSON.stringify({ ok: true, items: [] }), { status: 200 });
      }
      if (url === "/api/bff/candidate/files/upload") {
        return new Response(JSON.stringify({ ok: true, file_id: FILE_ID, scan_status: "CLEAN" }), { status: 201 });
      }
      if (url === `/api/bff/candidate/log-entries/${ENTRY_ID}/evidence` && method === "POST") {
        return new Response(
          JSON.stringify({ ok: true, id: "ev-1", entry_id: ENTRY_ID, file_id: FILE_ID, visibility: "HOST_AND_ACADEMIC" }),
          { status: 201 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onAttached = vi.fn();
    render(
      <TaskEvidenceDrawer
        isOpen
        entryId={ENTRY_ID}
        taskTitle="API integratsiyasi"
        locked={false}
        onClose={vi.fn()}
        onAttached={onAttached}
      />
    );

    await waitFor(() => expect(screen.getByText(/Hozircha dalil biriktirilmagan/i)).toBeTruthy());

    const input = screen.getByLabelText(/PDF fayl tanlash/i) as HTMLInputElement;
    const pdfFile = new File(["%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"], "dalil.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole("button", { name: /Yuklash va biriktirish/i }));

    await waitFor(() => expect(onAttached).toHaveBeenCalledTimes(1));
    expect(calls.some((c) => c.url === "/api/bff/candidate/files/upload" && c.body?.purpose === "PORTFOLIO")).toBe(true);
    expect(
      calls.some(
        (c) =>
          c.url === `/api/bff/candidate/log-entries/${ENTRY_ID}/evidence` &&
          c.method === "POST" &&
          c.body?.file_id === FILE_ID
      )
    ).toBe(true);
  });
});
