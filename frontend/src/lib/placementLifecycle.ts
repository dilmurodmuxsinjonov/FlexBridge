import { errorText } from "@/lib/errorText";

export interface PlanTaskDraft {
  code: string;
  title: string;
  expected_result: string;
  required: boolean;
  target_minutes?: number | null;
}

export interface HostPlacementPlan {
  placement_id: string;
  status: string;
  terms_id: string;
  version: number;
  start_date: string;
  end_date: string;
  academic_required: boolean;
  title?: string | null;
  objectives?: string | null;
  daily_limit_minutes: number;
  weekly_limit_minutes: number;
  required_minutes: number;
  tasks: PlanTaskDraft[];
}

export interface OrgMentorOption {
  user_id: string;
  membership_id: string;
  display_name: string;
}

export interface PlacementMentorAssignmentItem {
  id: string;
  placement_id: string;
  membership_id: string;
  mentor_user_id: string;
  display_name: string;
  assigned_at: string | null;
  accepted_at: string | null;
}

export interface LogEvidenceItem {
  id: string;
  entry_id: string;
  file_id: string;
  visibility: string;
  filename?: string | null;
  mime_type?: string | null;
  byte_size?: number | null;
  created_at?: string | null;
}

export interface PlacementCompletionResult {
  status?: string;
  placement_status?: string;
  decision?: string;
  [key: string]: unknown;
}

export interface PlacementExportResult {
  export_id: string;
  placement_id: string;
  file_id: string;
  export_format: string;
  created_at: string;
  expires_at: string;
  download_url: string;
  disclaimer: string;
  summary: Record<string, unknown>;
}

async function req<T>(url: string, init: RequestInit, fallbackError: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store", ...init });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const err = new Error(errorText(data, fallbackError));
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as T;
}

const json = (method: "POST" | "PUT", body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: JSON.stringify(body),
});

export function fetchHostPlacementPlan(placementId: string) {
  return req<HostPlacementPlan>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/plan`,
    { method: "GET", headers: { Accept: "application/json" } },
    "PLACEMENT_PLAN_FETCH_FAILED"
  );
}

export function fetchPlacementPlanNeutral(placementId: string) {
  return req<HostPlacementPlan>(
    `/api/bff/placements/${encodeURIComponent(placementId)}/plan`,
    { method: "GET", headers: { Accept: "application/json" } },
    "PLACEMENT_PLAN_FETCH_FAILED"
  );
}

export function publishHostPlacementPlan(
  placementId: string,
  payload: {
    terms_id: string;
    version: number;
    title: string;
    objectives: string;
    daily_limit_minutes: number;
    weekly_limit_minutes: number;
    required_minutes: number;
    tasks: PlanTaskDraft[];
  }
) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/plan`,
    json("PUT", { ...payload, idempotency_key: crypto.randomUUID() }),
    "PLACEMENT_PLAN_PUBLISH_FAILED"
  );
}

export async function fetchOrgMentors(orgId: string): Promise<OrgMentorOption[]> {
  const data = await req<{ items?: OrgMentorOption[] }>(
    `/api/bff/employer/organization/${encodeURIComponent(orgId)}/mentors`,
    { method: "GET", headers: { Accept: "application/json" } },
    "ORG_MENTORS_FETCH_FAILED"
  );
  return data.items || [];
}

export async function fetchPlacementMentorAssignments(
  placementId: string
): Promise<PlacementMentorAssignmentItem[]> {
  const data = await req<{ items?: PlacementMentorAssignmentItem[] }>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/mentor-assignments`,
    { method: "GET", headers: { Accept: "application/json" } },
    "MENTOR_ASSIGNMENTS_FETCH_FAILED"
  );
  return data.items || [];
}

export function nominatePlacementMentor(placementId: string, mentorUserId: string) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/mentor-assignments`,
    json("POST", { mentor_id: mentorUserId, idempotency_key: crypto.randomUUID() }),
    "MENTOR_NOMINATION_FAILED"
  );
}

export function revokePlacementMentor(
  placementId: string,
  assignmentId: string,
  termsId: string,
  version: number
) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/mentor-assignments/${encodeURIComponent(assignmentId)}/revoke`,
    json("POST", { terms_id: termsId, version, idempotency_key: crypto.randomUUID() }),
    "MENTOR_REVOKE_FAILED"
  );
}

export function acceptPlacementAssignment(
  placementId: string,
  assignmentId: string,
  termsId: string,
  version: number,
  assignmentKind: "MENTOR" | "TEACHER"
) {
  return req<Record<string, unknown>>(
    `/api/bff/placements/${encodeURIComponent(placementId)}/assignments/${encodeURIComponent(assignmentId)}/accept`,
    json("POST", {
      terms_id: termsId,
      version,
      assignment_kind: assignmentKind,
      idempotency_key: crypto.randomUUID(),
    }),
    "ASSIGNMENT_ACCEPT_FAILED"
  );
}

export function submitHostDecision(
  placementId: string,
  termsId: string,
  version: number,
  action: "ACTIVATE" | "CANCEL"
) {
  return req<Record<string, unknown>>(
    `/api/bff/employer/placements/${encodeURIComponent(placementId)}/host-decisions`,
    json("POST", { terms_id: termsId, version, action, idempotency_key: crypto.randomUUID() }),
    "HOST_DECISION_FAILED"
  );
}

export function submitCompletionRequest(
  placementId: string,
  payload: {
    terms_id: string;
    version: number;
    decision: "REQUEST_COMPLETION" | "CONFIRM_COMPLETION" | "REJECT_COMPLETION";
    reason?: string;
    early_reason?: string;
  }
) {
  return req<PlacementCompletionResult>(
    `/api/bff/placements/${encodeURIComponent(placementId)}/completion-requests`,
    json("POST", { ...payload, idempotency_key: crypto.randomUUID() }),
    "COMPLETION_REQUEST_FAILED"
  );
}

export function exportPlacementReport(
  placementId: string,
  format: "PDF" | "JSON" = "PDF",
  includeReviews = true
) {
  return req<PlacementExportResult>(
    `/api/bff/placements/${encodeURIComponent(placementId)}/exports`,
    json("POST", { format, include_reviews: includeReviews, idempotency_key: crypto.randomUUID() }),
    "PLACEMENT_EXPORT_FAILED"
  );
}

export function fetchFileDownloadUrl(fileId: string) {
  return req<{ signed_url?: string; url?: string }>(
    `/api/bff/files/${encodeURIComponent(fileId)}/download`,
    { method: "GET", headers: { Accept: "application/json" } },
    "FILE_DOWNLOAD_FAILED"
  );
}

export async function fetchLogEntryEvidence(entryId: string): Promise<LogEvidenceItem[]> {
  const data = await req<{ items?: LogEvidenceItem[] }>(
    `/api/bff/candidate/log-entries/${encodeURIComponent(entryId)}/evidence`,
    { method: "GET", headers: { Accept: "application/json" } },
    "LOG_EVIDENCE_LIST_FAILED"
  );
  return data.items || [];
}

export function attachLogEntryEvidence(
  entryId: string,
  fileId: string,
  visibility: "HOST_AND_ACADEMIC" | "HOST_ONLY" | "ACADEMIC_ONLY" = "HOST_AND_ACADEMIC"
) {
  return req<LogEvidenceItem>(
    `/api/bff/candidate/log-entries/${encodeURIComponent(entryId)}/evidence`,
    json("POST", { file_id: fileId, visibility }),
    "LOG_EVIDENCE_ATTACH_FAILED"
  );
}

export function createStudentSupervision(payload: {
  institution_id: string;
  enrollment_id: string;
  agreement_id: string;
  purpose: string;
  legal_basis: string;
}) {
  return req<Record<string, unknown>>(
    "/api/bff/university/supervisions",
    json("POST", { ...payload, idempotency_key: crypto.randomUUID() }),
    "SUPERVISION_CREATE_FAILED"
  );
}

export async function fetchSupervisionAssignments(supervisionId: string) {
  const data = await req<{ items?: Array<{ id: string; placement_id: string; supervisor_name?: string; accepted_at?: string | null; revoked_at?: string | null }> }>(
    `/api/bff/university/supervisions/${encodeURIComponent(supervisionId)}/assignments`,
    { method: "GET", headers: { Accept: "application/json" } },
    "SUPERVISION_ASSIGNMENTS_FETCH_FAILED"
  );
  return data.items || [];
}

export function revokeAcademicAssignment(assignmentId: string) {
  return req<Record<string, unknown>>(
    `/api/bff/university/academic-assignments/${encodeURIComponent(assignmentId)}/revoke`,
    json("POST", { idempotency_key: crypto.randomUUID() }),
    "ACADEMIC_REVOKE_FAILED"
  );
}
