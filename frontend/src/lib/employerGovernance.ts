import { errorText } from "@/lib/errorText";

export interface DraftMetadataInput {
  title?: string;
  description?: string;
  region?: string;
  work_mode?: "ONSITE" | "HYBRID" | "REMOTE";
  eligibility?: "ALL_CANDIDATES" | "STUDENTS_ONLY" | "ACADEMIC_TRIPARTITE" | "OPEN";
  capacity?: number;
  contract_type?: string;
  program_required?: string | null;
}

export interface DraftTermsInput {
  is_paid: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  salary_period?: "HOUR" | "MONTH" | null;
  salary_basis?: "GROSS" | "NET" | null;
  start_date?: string | null;
  end_date?: string | null;
  program_required?: string | null;
  fee_terms_note?: string | null;
}

export interface DraftShiftInput {
  weekday: number;
  start_minute: number;
  end_minute: number;
  group_code: string;
  timezone?: string;
}

export interface DraftScheduleInput {
  schedule_policy: "STRICT" | "NEGOTIABLE" | "FIXED";
  shift_match_mode: "ALL" | "ANY";
  shifts: DraftShiftInput[];
}

export interface VerifiedContactItem {
  id: string;
  channel: string;
  masked_destination: string;
  verified_at?: string | null;
  is_primary?: boolean;
}

export interface IncomingOwnerCaseItem {
  case_id: string;
  organization_id: string;
  public_name: string;
  status: string;
  current_revision: number;
  created_at: string;
}

export interface OrgContinuityCaseItem {
  id: string;
  status: string;
  created_at: string;
  applicant_id: string;
  applicant_display_name: string;
}

async function req<T>(url: string, init: RequestInit, fallbackError: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store", ...init });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const err = new Error(errorText(data, fallbackError));
    (err as unknown as { status: number; code?: string }).status = res.status;
    (err as unknown as { code?: string }).code = typeof data?.error === "string" ? data.error : undefined;
    throw err;
  }
  return data as T;
}

const jsonInit = (method: "POST" | "PUT" | "PATCH", body: unknown, withIdempotency = false): RequestInit => ({
  method,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(withIdempotency ? { "Idempotency-Key": crypto.randomUUID() } : {}),
  },
  body: JSON.stringify(body),
});

export function updateOpportunityDraft(opportunityId: string, payload: DraftMetadataInput) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/opportunities/${encodeURIComponent(opportunityId)}/draft`,
    jsonInit("PUT", payload),
    "DRAFT_UPDATE_FAILED"
  );
}

export function updateOpportunityTerms(opportunityId: string, payload: DraftTermsInput) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/opportunities/${encodeURIComponent(opportunityId)}/draft/terms`,
    jsonInit("PUT", payload),
    "DRAFT_TERMS_UPDATE_FAILED"
  );
}

export function updateOpportunitySchedule(opportunityId: string, payload: DraftScheduleInput) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/opportunities/${encodeURIComponent(opportunityId)}/draft/schedule`,
    jsonInit("PUT", payload),
    "DRAFT_SCHEDULE_UPDATE_FAILED"
  );
}

export function patchOrganizationProfile(
  orgId: string,
  payload: {
    legal_name?: string;
    public_name?: string;
    region?: string;
    description?: string | null;
    website?: string | null;
    file_ids: string[];
    evidence_note: string;
  }
) {
  return req<{ organization_id: string; changed: boolean; case_id: string | null; status?: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}`,
    jsonInit("PATCH", payload),
    "ORGANIZATION_UPDATE_FAILED"
  );
}

export async function fetchVerifiedContacts(): Promise<VerifiedContactItem[]> {
  const data = await req<{ items?: VerifiedContactItem[] }>(
    "/api/bff/me/contacts",
    { method: "GET", headers: { Accept: "application/json" } },
    "CONTACTS_FETCH_FAILED"
  );
  return (data.items || []).filter((c) => Boolean(c.verified_at));
}

export function submitOwnerAddition(
  orgId: string,
  payload: { target_membership_id: string; file_ids: string[]; evidence_note: string }
) {
  return req<{ id: string; status: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/owner-requests`,
    jsonInit("POST", payload, true),
    "OWNER_REQUEST_FAILED"
  );
}

export function submitOwnerTransfer(
  orgId: string,
  payload: { target_membership_id: string; file_ids: string[]; evidence_note: string }
) {
  return req<{ id: string; status: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/owner-transfers`,
    jsonInit("POST", payload, true),
    "OWNER_TRANSFER_FAILED"
  );
}

export async function fetchIncomingOwnerRequests(): Promise<IncomingOwnerCaseItem[]> {
  const data = await req<{ items?: IncomingOwnerCaseItem[] }>(
    "/api/bff/me/owner-requests",
    { method: "GET", headers: { Accept: "application/json" } },
    "OWNER_REQUESTS_FETCH_FAILED"
  );
  return data.items || [];
}

export async function fetchIncomingOwnerTransfers(): Promise<IncomingOwnerCaseItem[]> {
  const data = await req<{ items?: IncomingOwnerCaseItem[] }>(
    "/api/bff/me/owner-transfers",
    { method: "GET", headers: { Accept: "application/json" } },
    "OWNER_TRANSFERS_FETCH_FAILED"
  );
  return data.items || [];
}

export function respondOwnerCase(
  kind: "requests" | "transfers",
  caseId: string,
  payload: { expected_revision: number; decision: "ACCEPT" | "DECLINE"; contact_id?: string | null }
) {
  const path = kind === "requests" ? "owner-requests" : "owner-transfers";
  return req<{ id: string; status: string }>(
    `/api/bff/me/${path}/${encodeURIComponent(caseId)}/consent`,
    jsonInit("POST", payload),
    "OWNER_REQUEST_ACTION_FAILED"
  );
}

export async function fetchOrgContinuityCases(orgId: string): Promise<OrgContinuityCaseItem[]> {
  const data = await req<{ items?: OrgContinuityCaseItem[] }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/owner-continuity`,
    { method: "GET", headers: { Accept: "application/json" } },
    "OWNER_CONTINUITY_LIST_FAILED"
  );
  return data.items || [];
}

export function submitOrgContinuity(
  orgId: string,
  payload: { contact_id: string; file_ids: string[]; evidence_note: string }
) {
  return req<{ id: string; status: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/owner-continuity`,
    jsonInit("POST", payload, true),
    "OWNER_CONTINUITY_SUBMIT_FAILED"
  );
}

export function objectOrgContinuity(orgId: string, caseId: string, reason: string) {
  return req<{ id: string; status: string }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/owner-continuity/${encodeURIComponent(caseId)}/object`,
    jsonInit("POST", { reason }),
    "OWNER_CONTINUITY_OBJECT_FAILED"
  );
}
