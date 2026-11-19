import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import EnrollmentResubmitModal from "../nomzod/EnrollmentResubmitModal";
import RejectedAppealModal from "../employer/RejectedAppealModal";
import PlacementLifecycleModal from "../employer/PlacementLifecycleModal";
import {
  confirmPlacementStart,
  previewScheduleMatch,
  requestPlacementAcademicTrack,
} from "@/lib/placementLifecycle";

const ORG_ID = "11111111-1111-4111-8111-111111111111";
const PLC_ID = "22222222-2222-4222-8222-222222222222";
const TERMS_ID = "33333333-3333-4333-8333-333333333333";
const ENR_ID = "44444444-4444-4444-8444-444444444444";
const ACTION_ID = "55555555-5555-4555-8555-555555555555";
const FILE_ID = "66666666-6666-4666-8666-666666666666";
const OPP_ID = "77777777-7777-4777-8777-777777777777";

describe("Phase E remaining R1 user flows", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uploads PDF evidence and resubmits candidate enrollment verification", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === "/api/bff/candidate/files/upload") {
        return new Response(
          JSON.stringify({ ok: true, file_id: FILE_ID, sha256: "abc123", size_bytes: 12 }),
          { status: 201 }
        );
      }
      if (url === `/api/bff/candidate/enrollments/${ENR_ID}/verification`) {
        return new Response(
          JSON.stringify({ ok: true, enrollment_id: ENR_ID, revision: 2, status: "PENDING" }),
          { status: 200 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSaved = vi.fn();
    const onClose = vi.fn();
    render(
      <EnrollmentResubmitModal
        enrollment={{
          id: ENR_ID,
          institution_id: ORG_ID,
          institution_name: "TATU",
          program: "Dasturiy injiniring",
          start_date: "2024-09-02",
          end_date: "2028-06-30",
          current_student: true,
          reviewed: false,
          status: "PENDING",
          case_status: "NEEDS_INFO",
          revision: 1,
        }}
        onSaved={onSaved}
        onClose={onClose}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = new File(["%PDF-1.4\n"], "proof.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput, { target: { files: [pdfFile] } });

    const noteArea = screen.getByPlaceholderText(/OTM dekanati/i);
    fireEvent.change(noteArea, {
      target: { value: "Yangilangan dekanka ma'lumotnomasi va buyruq nusxasi ilova qilindi." },
    });

    fireEvent.click(screen.getByRole("button", { name: /Qayta yuborish/i }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(onClose).toHaveBeenCalledTimes(1);
    const submitCall = calls.find((c) => c.url === `/api/bff/candidate/enrollments/${ENR_ID}/verification`);
    expect(submitCall?.body?.expected_revision).toBe(1);
    expect(submitCall?.body?.file_ids).toEqual([FILE_ID]);
  });

  it("submits employer moderation appeal for a rejected opportunity", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });
      if (url === `/api/bff/employer/moderation/actions/${ACTION_ID}/appeals`) {
        return new Response(
          JSON.stringify({ ok: true, case_id: "88888888-8888-4888-8888-888888888888", status: "PENDING" }),
          { status: 201 }
        );
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSubmitted = vi.fn();
    render(
      <RejectedAppealModal
        isOpen
        opportunityTitle="Backend stajyor"
        actionId={ACTION_ID}
        onClose={() => {}}
        onSubmitted={onSubmitted}
      />
    );

    const reasonInput = screen.getByPlaceholderText(/qo‘shimcha dalil/i);
    fireEvent.change(reasonInput, {
      target: { value: "Mehnat shartnomasi va ish haqi shartlari qonunchilikka to'liq moslashtirildi." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Apellyatsiyani yuborish/i }));

    await waitFor(() => expect(screen.getByText(/Apellyatsiya yuborildi/i)).toBeTruthy());
    expect(onSubmitted).toHaveBeenCalledTimes(1);
    expect(calls[0].url).toBe(`/api/bff/employer/moderation/actions/${ACTION_ID}/appeals`);
  });

  it("confirms host placement start inside PlacementLifecycleModal and dispatches matching/academic helpers", async () => {
    const calls: Array<{ url: string; method: string; body?: Record<string, unknown> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = init?.method || "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
      calls.push({ url, method, body });

      if (url === `/api/bff/employer/placements/${PLC_ID}/plan`) {
        return new Response(
          JSON.stringify({
            ok: true,
            status: "PENDING_START_CONFIRMATION",
            terms_id: TERMS_ID,
            version: 2,
            title: "Dasturchi amaliyoti",
            objectives: "Backend API",
            daily_limit_minutes: 240,
            weekly_limit_minutes: 1200,
            required_minutes: 4800,
            tasks: [{ code: "T1", title: "FastAPI", expected_result: "PR", required: true, target_minutes: 120 }],
          }),
          { status: 200 }
        );
      }
      if (url.includes("/mentors")) {
        return new Response(JSON.stringify({ ok: true, items: [] }), { status: 200 });
      }
      if (url.includes("/assignments")) {
        return new Response(JSON.stringify({ ok: true, items: [] }), { status: 200 });
      }
      if (url === `/api/bff/placements/${PLC_ID}/confirm-start`) {
        return new Response(JSON.stringify({ ok: true, placement_status: "ACTIVE" }), { status: 200 });
      }
      if (url === `/api/bff/placements/${PLC_ID}/academic-requests`) {
        return new Response(JSON.stringify({ ok: true, supervision_id: "99999999-9999-4999-8999-999999999999" }), {
          status: 201,
        });
      }
      if (url === "/api/bff/matching/preview") {
        return new Response(JSON.stringify({ ok: true, result: "MATCH", matched_group_codes: ["SHIFT_1"] }), {
          status: 200,
        });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const onUpdated = vi.fn();
    render(
      <PlacementLifecycleModal
        isOpen
        orgId={ORG_ID}
        placement={{
          id: PLC_ID,
          application_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          offer_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          candidate_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          organization_id: ORG_ID,
          academic_track: true,
          status: "PENDING_START_CONFIRMATION",
          start_date: "2026-11-20",
          end_date: "2026-12-20",
          version: 2,
          current_terms_id: TERMS_ID,
        }}
        onClose={() => {}}
        onUpdated={onUpdated}
      />
    );

    await waitFor(() => expect(screen.getByDisplayValue("Dasturchi amaliyoti")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Mentor & Holat/i }));
    fireEvent.click(screen.getByRole("button", { name: /Boshlashni tasdiqlash \(Korxona\)/i }));

    await waitFor(() => expect(onUpdated).toHaveBeenCalledTimes(1));
    const confirmCall = calls.find((c) => c.url === `/api/bff/placements/${PLC_ID}/confirm-start`);
    expect(confirmCall?.body?.party).toBe("ORGANIZATION");
    expect(confirmCall?.body?.terms_id).toBe(TERMS_ID);

    await confirmPlacementStart(PLC_ID, TERMS_ID, 2, "CANDIDATE");
    expect(
      calls.some(
        (c) => c.url === `/api/bff/placements/${PLC_ID}/confirm-start` && c.body?.party === "CANDIDATE"
      )
    ).toBe(true);

    await requestPlacementAcademicTrack(PLC_ID, ENR_ID, TERMS_ID, 2);
    expect(
      calls.some(
        (c) =>
          c.url === `/api/bff/placements/${PLC_ID}/academic-requests` && c.body?.enrollment_id === ENR_ID
      )
    ).toBe(true);

    const match = await previewScheduleMatch(OPP_ID);
    expect(match.result).toBe("MATCH");
    expect(match.matched_group_codes).toEqual(["SHIFT_1"]);
  });
});
