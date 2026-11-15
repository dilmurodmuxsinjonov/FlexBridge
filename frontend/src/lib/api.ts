export interface Opportunity {
  id: string;
  organization_id: string;
  organization_name: string;
  organization_region: string | null;
  title: string;
  description: string | null;
  region: string | null;
  kind: string;
  work_mode: string | null;
  contract_type: string | null;
  is_paid: boolean;
  salary_min: number | null;
  salary_max: number | null;
  currency: string;
  schedule_policy: string | null;
  capacity: number;
  occupied_count: number;
  vacancies_available: number;
  published_at: string | null;
  expires_at: string | null;
}

export interface OpportunityPage {
  items: Opportunity[];
  has_more: boolean;
  next_after: string | null;
}

export interface CandidateApplication {
  id: string;
  student_name: string;
  student_id: string;
  university: string;
  course: string;
  gpa: number;
  match_score: number;
  shift_compatibility: "To‘liq mos" | "Qisman mos" | "Mos emas";
  stage: "new" | "review" | "interview" | "offered";
  skills: string[];
  submission_date: string;
  mentor?: string;
  interview_time?: string;
}

export interface InternshipDiaryEntry {
  student_id: string;
  student_name: string;
  university: string;
  course: string;
  company_name: string;
  mentor_name: string;
  week_number: number;
  period: string;
  mentor_review: string;
  mentor_score: number;
  teacher_review: string;
  teacher_name: string;
  compliance_verified: boolean;
  hours_completed: number;
  grade_score: number;
  status: "pending_review" | "verified_hemis" | "flagged";
}

export interface SecurityAuditEvent {
  event_id: string;
  timestamp: string;
  actor_role: string;
  ip_address: string;
  sha256_hash: string;
  event_type: "BREAK_GLASS_REQUEST" | "CONTRACT_SIGN" | "WAF_BLOCK" | "DIARY_VERIFICATION" | "REESTR_SYNC";
  details: string;
  status_badge: "warning" | "verified" | "danger" | "info" | "neutral";
}

// ---------------------------------------------------------------------------
// BFF & Server-Session Types (FB-140B)
// ---------------------------------------------------------------------------

export interface AuthUser {
  user_id: string;
  session_id: string;
  roles: string[];
}

export type LoginResult =
  | { ok: true; mfa_required?: false; user_id: string; roles: string[] }
  | { ok: true; mfa_required: true; mfa_ticket: string; expires_in: number }
  | { ok: false; error: string };

export interface EmployerDashboardMetrics {
  contract_id: "API-068";
  organization_id: string;
  metrics: {
    opportunities: {
      total: number;
      published: number;
      draft: number;
      closed: number;
      paused: number;
    };
    applications: {
      total: number;
      pending: number;
      shortlisted: number;
      interviewed: number;
      offered: number;
      accepted: number;
      rejected: number;
      withdrawn: number;
    };
    engagements: {
      total: number;
      active: number;
      pending_start: number;
      completed: number;
      disputed: number;
    };
    interviews: {
      total: number;
      scheduled: number;
      completed: number;
      cancelled: number;
      no_show: number;
    };
  };
}

export interface AcademicReviewQueueItem {
  id: string;
  daily_log_id: string;
  placement_id: string;
  institution_id: string;
  purpose: string;
  local_date: string;
  revision: number;
  submitted_at: string;
  student_name: string;
}

export interface AcademicLogTaskEntry {
  id: string;
  plan_task_id: string | null;
  result_text: string;
  minutes: number;
  code: string | null;
  title: string | null;
}

export interface AcademicLogRevisionDetail {
  id: string;
  revision: number;
  terms_id: string;
  day_type: string;
  summary: string;
  total_minutes: number;
  submitted_at: string;
  daily_log_id: string;
  local_date: string;
  placement_id: string;
  placement_status: string;
  is_current_revision: boolean;
  institution_id: string;
  purpose: string;
  terms_version: number;
  tasks: AcademicLogTaskEntry[];
  workplace_reviews: Array<{
    id: string;
    mentor_assignment_id?: string;
    decision: string;
    comment: string;
    decided_at: string;
  }>;
  academic_reviews: Array<{
    id: string;
    academic_assignment_id?: string;
    decision: string;
    comment: string;
    decided_at: string;
  }>;
}

export interface SubmitAcademicReviewPayload {
  academic_assignment_id?: string;
  decision: "REVIEWED" | "NEEDS_REVISION";
  comment?: string;
  idempotency_key?: string;
}

export interface AcademicReviewResult {
  id: string;
  revision_id: string;
  placement_id: string;
  academic_assignment_id: string;
  decision: string;
  comment: string;
  decided_at: string;
}

export interface OperatorAuditEventItem {
  id: string;
  occurred_at: string;
  actor_id: string;
  session_id: string;
  action: string;
  object_type: string;
  object_key: string;
  before_digest: string | null;
  after_digest: string | null;
  reason: string | null;
}

type OpportunitySearch = {
  query?: string;
  region?: string;
  is_paid?: boolean;
  after?: string;
  signal?: AbortSignal;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isOpportunity(value: unknown): value is Opportunity {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.organization_id === "string" &&
    typeof value.title === "string" &&
    typeof value.organization_name === "string" &&
    isNullableString(value.organization_region) &&
    isNullableString(value.description) &&
    isNullableString(value.region) &&
    typeof value.kind === "string" &&
    isNullableString(value.work_mode) &&
    isNullableString(value.contract_type) &&
    typeof value.is_paid === "boolean" &&
    isNullableNumber(value.salary_min) &&
    isNullableNumber(value.salary_max) &&
    typeof value.currency === "string" &&
    isNullableString(value.schedule_policy) &&
    Number.isInteger(value.capacity) &&
    Number.isInteger(value.occupied_count) &&
    Number.isInteger(value.vacancies_available) &&
    (value.vacancies_available as number) >= 0 &&
    isNullableString(value.published_at) &&
    isNullableString(value.expires_at)
  );
}

export async function fetchOpportunities(params: OpportunitySearch = {}): Promise<OpportunityPage> {
  const query = new URLSearchParams({ limit: "12" });
  if (params.query) query.set("query", params.query);
  if (params.region) query.set("region", params.region);
  if (params.is_paid !== undefined) query.set("is_paid", String(params.is_paid));
  if (params.after) query.set("after", params.after);

  const response = await fetch(`/api/backend/opportunities?${query}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal: params.signal,
  });
  if (!response.ok) throw new Error("OPPORTUNITIES_REQUEST_FAILED");

  const data: unknown = await response.json();
  if (
    !isRecord(data) ||
    data.contract_id !== "API-001" ||
    !Array.isArray(data.items) ||
    !data.items.every(isOpportunity) ||
    typeof data.has_more !== "boolean" ||
    (data.next_after !== null && typeof data.next_after !== "string") ||
    (data.has_more && !data.next_after)
  ) {
    throw new Error("OPPORTUNITIES_RESPONSE_INVALID");
  }
  return {
    items: data.items,
    has_more: data.has_more,
    next_after: data.next_after,
  };
}

// ---------------------------------------------------------------------------
// Client BFF Methods
// ---------------------------------------------------------------------------

export async function loginUser(
  destination: string,
  password: string,
  totp_code?: string
): Promise<LoginResult> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ destination, password, totp_code }),
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 202) {
    return {
      ok: true,
      mfa_required: true,
      mfa_ticket: data.mfa_ticket,
      expires_in: data.expires_in || 300,
    };
  }
  if (!res.ok) {
    return { ok: false, error: data.error || "LOGIN_FAILED" };
  }
  return {
    ok: true,
    user_id: data.user_id,
    roles: data.roles || [],
  };
}

export async function verifyMfa(mfa_ticket: string, code: string): Promise<LoginResult> {
  const res = await fetch("/api/auth/mfa/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ mfa_ticket, code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return { ok: false, error: data.error || "MFA_VERIFICATION_FAILED" };
  }
  return {
    ok: true,
    user_id: data.user_id,
    roles: data.roles || [],
  };
}

export async function logoutUser(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: { Accept: "application/json" },
  }).catch(() => {});
}

export async function fetchAuthMe(): Promise<AuthUser | null> {
  try {
    const res = await fetch("/api/auth/me", {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.ok || !data.user) return null;
    return data.user as AuthUser;
  } catch {
    return null;
  }
}

export async function fetchEmployerDashboard(
  orgId: string
): Promise<EmployerDashboardMetrics> {
  const res = await fetch(`/api/bff/employer/dashboard?org=${encodeURIComponent(orgId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "DASHBOARD_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as EmployerDashboardMetrics;
}

export async function fetchUniversityReviewQueue(): Promise<AcademicReviewQueueItem[]> {
  const res = await fetch("/api/bff/university/review-queue", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "REVIEW_QUEUE_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as AcademicReviewQueueItem[];
}

export async function fetchOperatorAuditEvents(): Promise<OperatorAuditEventItem[]> {
  const res = await fetch("/api/bff/operator/audit-events", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "AUDIT_EVENTS_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as OperatorAuditEventItem[];
}

export interface OpportunityDetail {
  contract_id: "API-005";
  id: string;
  organization_id: string;
  kind: string;
  status: string;
  capacity: number;
  occupied_count: number;
  vacancies_available: number;
  published_at: string | null;
  expires_at: string | null;
  closed_at: string | null;
  revision: {
    title: string;
    description: string | null;
    region: string | null;
    work_mode: string | null;
    eligibility: string | null;
    contract_type: string | null;
    is_paid: boolean;
    salary_min: number | null;
    salary_max: number | null;
    currency: string;
    salary_period: string | null;
    salary_basis: string | null;
    schedule_policy: string | null;
  };
  organization: {
    id: string;
    name: string;
    status: string;
    rating?: number | null;
  };
  skills: Array<{ id: string; name: string }>;
  shifts: Array<{
    id: string;
    group_code: string;
    weekday: number;
    start_minute: number;
    end_minute: number;
    is_required: boolean;
  }>;
}

export interface ApplicationSubmissionResult {
  ok: boolean;
  contract_id?: string;
  application_id?: string;
  error?: string;
  message?: string;
}

export async function fetchOpportunityDetail(id: string): Promise<OpportunityDetail> {
  const res = await fetch(`/api/bff/opportunities/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.error || "OPPORTUNITY_NOT_FOUND");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OpportunityDetail;
}

export async function submitOpportunityApplication(
  id: string,
  payload: { note?: string; enrollment_id?: string; proposed_slots?: string[] }
): Promise<ApplicationSubmissionResult> {
  const res = await fetch(`/api/bff/opportunities/${encodeURIComponent(id)}/apply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "APPLICATION_FAILED");
    (err as unknown as { status: number; code?: string }).status = res.status;
    (err as unknown as { code?: string }).code = data.detail?.code || data.error;
    throw err;
  }
  return {
    ok: true,
    contract_id: data.contract_id || "API-006",
    application_id: data.id || data.application_id,
  };
}

export async function createEmployerOpportunity(payload: {
  organization_id: string;
  title: string;
  opportunity_kind: string;
  contract_type: string;
  compensation_type: string;
  hourly_pay?: number | null;
  stipend_amount?: number | null;
  fee_terms_note?: string | null;
}): Promise<Record<string, unknown>> {
  const res = await fetch("/api/bff/employer/opportunities/create", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "CREATION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Candidate Applications Types & Helpers (FB-148 / API-029, 039, 041, 044, 040)
// ---------------------------------------------------------------------------

export interface CandidateApplicationsSummary {
  contract_id: "API-029";
  candidate_id: string;
  total_applications: number;
  submitted: number;
  under_review: number;
  interview_scheduled: number;
  interviews_total: number;
  offered: number;
  offers_total: number;
  accepted: number;
  rejected: number;
  withdrawn: number;
  expired: number;
}

export interface CandidateApplicationItem {
  id: string;
  opportunity_id: string;
  status: "SUBMITTED" | "UNDER_REVIEW" | "INTERVIEW_SCHEDULED" | "OFFERED" | "ACCEPTED" | "REJECTED" | "WITHDRAWN" | "EXPIRED";
  version: number;
  created_at: string;
  updated_at: string;
  opportunity: {
    id: string;
    title: string;
    organization_name: string;
    work_mode: string | null;
    contract_type: string | null;
    status: string;
  };
  current_attempt: {
    attempt_no: number;
    submitted_at: string;
    schedule_result: string | null;
  } | null;
}

export interface CandidateApplicationsListResponse {
  contract_id: "API-039";
  items: CandidateApplicationItem[];
  next_after: string | null;
}

export interface CandidateApplicationDetail {
  contract_id: "API-041";
  id: string;
  candidate_id: string;
  opportunity_id: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  occupied_at: string | null;
  released_at: string | null;
  opportunity: {
    id: string;
    title: string | null;
    organization_id: string | null;
    organization_name: string | null;
    work_mode: string | null;
    contract_type: string | null;
    status: string | null;
  };
  attempts: Array<{
    id: string;
    attempt_no: number;
    revision_id: string;
    enrollment_id: string | null;
    profile_snapshot: Record<string, unknown> | null;
    schedule_result: string | null;
    matching_version: string | null;
    proposed_slots: unknown[] | null;
    submitted_at: string;
  }>;
  timeline: Array<{
    id: string;
    attempt_id: string | null;
    actor_id: string;
    from_status: string;
    to_status: string;
    reason: string | null;
    occurred_at: string;
  }>;
  interview: {
    id: string;
    starts_at: string;
    ends_at: string;
    timezone: string;
    mode: string;
    location_or_link: string;
    status: string;
  } | null;
  offer: {
    id: string;
    status: string;
    terms_snapshot: Record<string, unknown> | null;
    expires_at: string | null;
    accepted_at: string | null;
  } | null;
}

export async function fetchCandidateApplicationsSummary(): Promise<CandidateApplicationsSummary> {
  const res = await fetch("/api/bff/candidate/applications/summary", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUMMARY_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateApplicationsSummary;
}

export async function fetchCandidateApplications(params?: {
  status?: string;
  limit?: number;
  after?: string;
}): Promise<CandidateApplicationsListResponse> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.after) sp.set("after", params.after);
  const qs = sp.toString();

  const res = await fetch(`/api/bff/candidate/applications${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "APPLICATIONS_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateApplicationsListResponse;
}

export async function fetchCandidateApplicationDetail(id: string): Promise<CandidateApplicationDetail> {
  const res = await fetch(`/api/bff/candidate/applications/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "APPLICATION_DETAIL_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateApplicationDetail;
}

export async function withdrawCandidateApplication(
  id: string,
  reason?: string
): Promise<{ ok: boolean; message?: string; status?: string }> {
  const res = await fetch(`/api/bff/candidate/applications/${encodeURIComponent(id)}/withdraw`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ reason }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "WITHDRAW_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return { ok: true, message: data.message, status: data.status };
}

export async function reapplyCandidateApplication(
  id: string,
  payload: { reason?: string; proposed_slots?: unknown[] }
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/candidate/applications/${encodeURIComponent(id)}/reapply`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "REAPPLY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Employer Applications & Kanban Workflow (FB-150 / API-082, 083, 084, 085, 086)
// ---------------------------------------------------------------------------

export interface EmployerOpportunityApplicationItem {
  application_id: string;
  opportunity_id: string;
  candidate_id: string;
  status: "SUBMITTED" | "REVIEWING" | "SHORTLISTED" | "INVITED_TO_INTERVIEW" | "OFFER_PENDING" | "OFFERED" | "ACCEPTED" | "REJECTED" | "WITHDRAWN";
  attempt_no: number;
  headline?: string | null;
  region?: string | null;
  schedule_result?: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string;
}

export interface EmployerOpportunityApplicationsResponse {
  contract_id: "API-082";
  opportunity_id: string;
  items: EmployerOpportunityApplicationItem[];
  limit: number;
  has_more: boolean;
  next_cursor: string | null;
}

export interface ApplicationTransitionResult {
  contract_id: "API-083";
  application_id: string;
  from_status: string;
  to_status: string;
  version: number;
  transitioned_at: string;
}

export interface ApplicationHRDetailResponse {
  contract_id: "API-084";
  application_id: string;
  candidate_id: string;
  opportunity_id: string;
  status: string;
  version: number;
  attempt?: {
    attempt_id: string | null;
    attempt_no: number;
    revision_id: string | null;
    enrollment_id?: string | null;
    profile_snapshot: Record<string, unknown>;
    schedule_result: string | null;
    matching_version: string;
    proposed_slots?: unknown;
    submitted_at: string;
  } | null;
  snapshot?: Record<string, unknown>;
  events: Array<{
    id: string;
    from_status: string | null;
    to_status: string;
    reason: string | null;
    occurred_at: string;
  }>;
}

export interface ScheduleInterviewPayload {
  starts_at: string;
  ends_at: string;
  mode?: "ONLINE" | "IN_PERSON";
  location_or_link?: string;
  timezone?: string;
}

export interface ScheduleInterviewResult {
  contract_id: "API-085";
  id: string;
  application_id: string;
  status: "SCHEDULED";
  starts_at: string;
  ends_at: string;
  mode: string;
  timezone: string;
}

export interface IssueOfferPayload {
  expires_at?: string;
  terms_snapshot?: Record<string, unknown>;
  idempotency_key?: string;
}

export interface IssueOfferResult {
  contract_id: "API-086";
  id: string;
  application_id: string;
  status: "OFFERED";
  expires_at?: string | null;
  terms_snapshot?: Record<string, unknown> | null;
}

export async function fetchEmployerOpportunityApplications(
  oppId: string,
  params?: { status?: string; limit?: number; cursor?: string }
): Promise<EmployerOpportunityApplicationsResponse> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.cursor) sp.set("cursor", params.cursor);
  const qs = sp.toString();

  const res = await fetch(`/api/bff/employer/opportunities/${encodeURIComponent(oppId)}/applications${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "FETCH_APPLICATIONS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as EmployerOpportunityApplicationsResponse;
}

export async function transitionApplicationStatus(
  appId: string,
  payload: { to_status: string; reason?: string }
): Promise<ApplicationTransitionResult> {
  const res = await fetch(`/api/bff/employer/applications/${encodeURIComponent(appId)}/transition`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "TRANSITION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as ApplicationTransitionResult;
}

export async function fetchApplicationHRDetail(appId: string): Promise<ApplicationHRDetailResponse> {
  const res = await fetch(`/api/bff/employer/applications/${encodeURIComponent(appId)}/hr`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "FETCH_HR_DETAIL_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as ApplicationHRDetailResponse;
}

export async function scheduleApplicationInterview(
  appId: string,
  payload: ScheduleInterviewPayload
): Promise<ScheduleInterviewResult> {
  const res = await fetch(`/api/bff/employer/applications/${encodeURIComponent(appId)}/interviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "SCHEDULE_INTERVIEW_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as ScheduleInterviewResult;
}

export async function issueApplicationOffer(
  appId: string,
  payload?: IssueOfferPayload
): Promise<IssueOfferResult> {
  const res = await fetch(`/api/bff/employer/applications/${encodeURIComponent(appId)}/offers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload || {}),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "ISSUE_OFFER_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as IssueOfferResult;
}

export async function fetchAcademicLogRevision(revisionId: string): Promise<AcademicLogRevisionDetail> {
  const res = await fetch(`/api/bff/university/log-revisions/${encodeURIComponent(revisionId)}/academic`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.detail || data.message || data.error || "FETCH_REVISION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as AcademicLogRevisionDetail;
}

export async function submitAcademicLogReview(
  revisionId: string,
  payload: SubmitAcademicReviewPayload
): Promise<AcademicReviewResult> {
  const res = await fetch(`/api/bff/university/log-revisions/${encodeURIComponent(revisionId)}/academic-reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.detail || data.message || data.error || "SUBMIT_ACADEMIC_REVIEW_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as AcademicReviewResult;
}

// ---------------------------------------------------------------------------
// Candidate Internship Daily Logs (API-030, API-053, API-054, API-056)
// ---------------------------------------------------------------------------

export interface CandidatePlacementItem {
  id: string;
  status: string;
  start_date: string;
  end_date: string;
  academic_track: boolean;
  opportunity_id?: string;
  opportunity_title?: string;
  organization_id?: string;
  organization_name?: string;
  created_at: string;
  current_terms_id?: string;
}

export interface CandidatePlacementsResponse {
  contract_id: string;
  items: CandidatePlacementItem[];
  next_after?: string | null;
}

export interface DailyLogTaskItem {
  id?: string;
  title: string;
  minutes: number;
  start_minute?: number | null;
  end_minute?: number | null;
}

export interface DailyLogItem {
  id: string;
  local_date: string;
  placement_id: string;
  current_revision_id: string;
  revision: number;
  day_type: "WORKED" | "ABSENT";
  summary: string;
  total_minutes: number;
  status: "DRAFT" | "SUBMITTED" | "REVIEWED" | "NEEDS_REVISION";
  submitted_at?: string | null;
  tasks?: DailyLogTaskItem[];
  workplace_reviews?: Array<{ decision: string; comment?: string; decided_at: string }>;
  academic_reviews?: Array<{ decision: string; comment?: string; decided_at: string }>;
}

export interface PlacementLogsResponse {
  items: DailyLogItem[];
  total: number;
  page?: number;
  page_size?: number;
}

export interface SaveDraftDailyLogPayload {
  day_type?: "WORKED" | "ABSENT";
  summary_text?: string;
  total_minutes?: number;
  tasks?: Array<{
    title: string;
    minutes: number;
    start_minute?: number;
    end_minute?: number;
  }>;
}

export interface SubmitDailyLogResult {
  contract_id: string;
  id: string;
  placement_id: string;
  local_date: string;
  status: "SUBMITTED";
  [key: string]: unknown;
}

export async function fetchCandidatePlacements(): Promise<CandidatePlacementsResponse> {
  const res = await fetch("/api/bff/candidate/placements", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_PLACEMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidatePlacementsResponse;
}

export async function fetchPlacementLogs(
  placementId: string,
  params?: { from_date?: string; to_date?: string; status?: string }
): Promise<PlacementLogsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.from_date) searchParams.set("from_date", params.from_date);
  if (params?.to_date) searchParams.set("to_date", params.to_date);
  if (params?.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();

  const res = await fetch(`/api/bff/candidate/placements/${encodeURIComponent(placementId)}/logs${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_LOGS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as PlacementLogsResponse;
}

export async function saveDraftDailyLog(
  placementId: string,
  date: string,
  payload: SaveDraftDailyLogPayload
): Promise<DailyLogItem> {
  const res = await fetch(`/api/bff/candidate/placements/${encodeURIComponent(placementId)}/logs/${encodeURIComponent(date)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "SAVE_DRAFT_LOG_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as DailyLogItem;
}

export async function submitDailyLog(logId: string): Promise<SubmitDailyLogResult> {
  const res = await fetch(`/api/bff/candidate/logs/${encodeURIComponent(logId)}/submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail?.message || data.message || data.error || "SUBMIT_DAILY_LOG_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as SubmitDailyLogResult;
}

// ============================================================================
// Operator Portal (Verification Cases, Break-Glass, Emergency Revocation)
// ============================================================================

export interface OperatorVerificationCaseItem {
  id: string;
  kind?: string;
  entity_id?: string;
  entity_type?: string;
  revision?: number;
  status?: string;
  due_at?: string;
  assigned_to_id?: string | null;
  assigned_reviewer_id?: string | null;
  organization_name?: string;
  tax_id?: string;
  institution_name?: string;
}

export interface OperatorVerificationCasesResponse {
  ok: boolean;
  contract_id: string;
  items: OperatorVerificationCaseItem[];
}

export interface DecideVerificationCasePayload {
  decision: "APPROVE" | "REJECT" | "NEEDS_INFO";
  expected_revision: number;
  reason: string;
}

export interface DecideVerificationCaseResult {
  ok: boolean;
  contract_id: string;
  case_id?: string;
  decision?: string;
  status?: string;
}

export interface BreakGlassAccessPayload {
  target_user_id: string;
  role_code: string;
  reason: string;
  independent_approver_id: string;
  duration_minutes: number;
}

export interface BreakGlassAccessResult {
  ok: boolean;
  contract_id: string;
  grant_id?: string;
  target_user_id?: string;
  role_code?: string;
  expires_at?: string;
  duration_minutes?: number;
  status?: string;
}

export interface EmergencyRevokeSessionsPayload {
  reason: string;
  incident_id?: string | null;
}

export interface EmergencyRevokeSessionsResult {
  ok: boolean;
  contract_id: string;
  target_user_id?: string;
  revoked_count?: number;
  status?: string;
}

export async function fetchOperatorVerificationCases(params?: {
  limit?: number;
  unassigned?: boolean;
}): Promise<OperatorVerificationCaseItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.unassigned !== undefined) searchParams.set("unassigned", String(params.unassigned));
  const qs = searchParams.toString();

  const res = await fetch(`/api/bff/operator/verification-cases${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || "FETCH_CASES_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as OperatorVerificationCaseItem[];
}

export async function claimVerificationCase(
  caseId: string
): Promise<{ ok: boolean; [key: string]: unknown }> {
  const res = await fetch(`/api/bff/operator/verification-cases/${encodeURIComponent(caseId)}/claim`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "CLAIM_CASE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; [key: string]: unknown };
}

export async function decideVerificationCase(
  caseId: string,
  payload: DecideVerificationCasePayload
): Promise<DecideVerificationCaseResult> {
  const res = await fetch(`/api/bff/operator/verification-cases/${encodeURIComponent(caseId)}/decide`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "DECIDE_CASE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as DecideVerificationCaseResult;
}

export async function requestBreakGlassAccess(
  payload: BreakGlassAccessPayload
): Promise<BreakGlassAccessResult> {
  const res = await fetch(`/api/bff/operator/access-requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "BREAK_GLASS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as BreakGlassAccessResult;
}

export async function emergencyRevokeUserSessions(
  userId: string,
  payload: EmergencyRevokeSessionsPayload
): Promise<EmergencyRevokeSessionsResult> {
  const res = await fetch(`/api/bff/operator/users/${encodeURIComponent(userId)}/revoke-sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "REVOKE_SESSIONS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as EmergencyRevokeSessionsResult;
}

// ============================================================================
// Operator Support Tickets, Incidents, DR SLA & Analytics (FB-172)
// ============================================================================

export interface OperatorSupportTicketItem {
  id: string;
  category: string;
  status: string;
  priority: string;
  subject?: string;
  description?: string;
  creator_user_id?: string;
  assigned_to_id?: string | null;
  created_at: string;
  updated_at?: string;
  due_at?: string | null;
  messages_count?: number;
}

export interface PostOperatorTicketMessagePayload {
  body: string;
  internal?: boolean;
  status?: string;
  file_id?: string;
}

export interface OperatorTicketMessageResult {
  ok: boolean;
  contract_id: string;
  message_id?: string;
  ticket_id?: string;
  body?: string;
  internal?: boolean;
  status?: string;
  created_at?: string;
}

export interface DeclareOperatorIncidentPayload {
  severity: "P1" | "P2" | "P3" | "P4";
  title: string;
  summary?: string;
  commander_id?: string;
  commander_user_id?: string;
  postmortem_ref?: string;
}

export interface OperatorDeclareIncidentResult {
  ok: boolean;
  contract_id: string;
  incident_id: string;
  severity: string;
  title: string;
  status?: string;
  commander_user_id?: string;
  declared_at?: string;
}

export interface OperatorRestoreRunItem {
  id: string;
  target_db?: string;
  backup_snapshot_time?: string;
  completed_at?: string;
  rpo_minutes?: number;
  rto_minutes?: number;
  sla_met?: boolean;
  status?: string;
  verified_by?: string;
}

export interface OperatorRestoreRunsResponse {
  ok: boolean;
  contract_id: string;
  items: OperatorRestoreRunItem[];
  summary?: {
    rpo_sla_target_minutes?: number;
    rto_sla_target_minutes?: number;
    total_runs_evaluated?: number;
    all_sla_met?: boolean;
  };
}

export interface OperatorPlatformAnalytics {
  ok: boolean;
  contract_id: string;
  deduplication_effectiveness_pct?: number;
  mutual_start_rate_pct?: number;
  outbox_backlog_count?: number;
  active_circuits?: Record<string, string>;
  total_events_processed?: number;
  period?: {
    start_date?: string;
    end_date?: string;
  };
}

export async function fetchOperatorSupportTickets(params?: {
  status?: string;
  category?: string;
  priority?: string;
  assignee_id?: string;
  limit?: number;
  cursor?: string;
}): Promise<{ ok: boolean; contract_id: string; items: OperatorSupportTicketItem[]; next_cursor: string | null; total?: number }> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.category) search.set("category", params.category);
  if (params?.priority) search.set("priority", params.priority);
  if (params?.assignee_id) search.set("assignee_id", params.assignee_id);
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.cursor) search.set("cursor", params.cursor);

  const qs = search.toString();
  const res = await fetch(`/api/bff/operator/support-tickets${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_TICKETS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function postOperatorTicketMessage(
  ticketId: string,
  payload: PostOperatorTicketMessagePayload
): Promise<OperatorTicketMessageResult> {
  const res = await fetch(`/api/bff/operator/support-tickets/${encodeURIComponent(ticketId)}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "POST_MESSAGE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorTicketMessageResult;
}

export async function declareOperatorIncident(
  payload: DeclareOperatorIncidentPayload
): Promise<OperatorDeclareIncidentResult> {
  const res = await fetch(`/api/bff/operator/incidents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "DECLARE_INCIDENT_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorDeclareIncidentResult;
}

export async function fetchOperatorRestoreRuns(params?: {
  limit?: number;
  status?: string;
}): Promise<OperatorRestoreRunsResponse> {
  const search = new URLSearchParams();
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.status) search.set("status", params.status);

  const qs = search.toString();
  const res = await fetch(`/api/bff/operator/restore-runs${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_RESTORE_RUNS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorRestoreRunsResponse;
}

export async function fetchOperatorAnalytics(params?: {
  start_date?: string;
  end_date?: string;
  cohort?: string;
}): Promise<OperatorPlatformAnalytics> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);
  if (params?.cohort) search.set("cohort", params.cohort);

  const qs = search.toString();
  const res = await fetch(`/api/bff/operator/analytics${qs ? `?${qs}` : ""}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ANALYTICS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorPlatformAnalytics;
}

// ============================================================================
// Candidate Profile, Skills & Availability Management (FB-158)
// ============================================================================

export interface CandidateProfileSkill {
  skill_id: string;
  level: string;
  code: string;
  name_uz: string;
  name_ru: string;
  active: boolean;
  verified?: boolean;
}

export interface CandidateProfileData {
  id: string;
  user_id: string;
  headline?: string | null;
  region?: string | null;
  bio?: string | null;
  experience_months?: number;
  visibility?: string;
  cv_file_id?: string | null;
  skills: CandidateProfileSkill[];
}

export interface CatalogSkillItem {
  id: string;
  code: string;
  name_uz: string;
  name_ru: string;
  category?: string;
  active: boolean;
}

export interface AvailabilityRuleItem {
  id?: string;
  weekday: number; // 1 = Dushanba .. 7 = Yakshanba
  start_minute: number;
  end_minute: number;
  valid_from?: string;
  valid_to?: string | null;
  timezone?: string;
}

export interface AvailabilityScheduleDay {
  date: string;
  weekday: number;
  is_available: boolean;
  intervals: Array<{ start_minute: number; end_minute: number }>;
}

export interface AvailabilityScheduleResponse {
  ok: boolean;
  contract_id: string;
  rules?: AvailabilityRuleItem[];
  days?: AvailabilityScheduleDay[];
}

export interface UpdateCandidateProfilePayload {
  headline?: string;
  region?: string;
  bio?: string | null;
  experience_months?: number;
}

export interface UpdateCandidateSkillsPayload {
  skills?: Array<{ skill_id: string; level: string }>;
  remove_skill_ids?: string[];
}

export async function fetchCandidateProfile(): Promise<CandidateProfileData> {
  const res = await fetch(`/api/bff/candidate/profile`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_PROFILE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data.profile as CandidateProfileData;
}

export async function updateCandidateProfile(
  payload: UpdateCandidateProfilePayload
): Promise<CandidateProfileData> {
  const res = await fetch(`/api/bff/candidate/profile`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "UPDATE_PROFILE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateProfileData;
}

export async function fetchCatalogSkills(q = ""): Promise<CatalogSkillItem[]> {
  const sp = new URLSearchParams();
  if (q) sp.set("q", q);
  sp.set("limit", "100");

  const res = await fetch(`/api/bff/candidate/skills?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_SKILLS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as CatalogSkillItem[];
}

export async function updateCandidateSkills(
  payload: UpdateCandidateSkillsPayload
): Promise<{ ok: boolean; [key: string]: unknown }> {
  const res = await fetch(`/api/bff/candidate/skills`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "UPDATE_SKILLS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; [key: string]: unknown };
}

export async function fetchCandidateAvailability(
  fromDate?: string,
  days = 28
): Promise<AvailabilityScheduleResponse> {
  const sp = new URLSearchParams();
  if (fromDate) sp.set("from_date", fromDate);
  sp.set("days", String(days));

  const res = await fetch(`/api/bff/candidate/availability?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_AVAILABILITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as AvailabilityScheduleResponse;
}

export async function saveCandidateAvailability(
  rules: AvailabilityRuleItem[]
): Promise<{ ok: boolean; [key: string]: unknown }> {
  const res = await fetch(`/api/bff/candidate/availability`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ rules }),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SAVE_AVAILABILITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; [key: string]: unknown };
}

// ---------------------------------------------------------------------------
// University Placements, Conclusions & Nomination Types & Helpers (FB-160 / API-102, 103, 104, 108)
// ---------------------------------------------------------------------------

export interface TeacherAcademicAssignmentItem {
  id: string;
  placement_id: string;
  institution_id: string;
  assigned_at: string;
  accepted_at: string | null;
  student_name?: string;
  organization_name?: string;
  status?: string;
}

export interface AcademicDecisionContext {
  ok: boolean;
  contract_id: "API-108-CONTEXT";
  placement_id: string;
  academic_assignment_id: string;
  terms_id: string;
  version: number;
  basis_digest: string;
  log_count: number;
  submitted_count: number;
  reviewed_count: number;
  needs_revision_count: number;
  current_conclusion?: {
    receipt?: Record<string, unknown>;
    decision?: string;
    concluded_at?: string;
  } | null;
  decision_eligible: boolean;
}

export interface CoordinatorAssignmentQueueItem {
  id: string;
  request_revision: number;
  placement_id: string;
  enrollment_id: string;
  institution_id: string;
  terms_id: string;
  student_name: string;
}

export interface AcademicTeacherOption {
  id: string;
  display_name: string;
}

export async function fetchTeacherAcademicAssignments(limit = 50): Promise<TeacherAcademicAssignmentItem[]> {
  const res = await fetch(`/api/bff/university/assignments?limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ASSIGNMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as TeacherAcademicAssignmentItem[];
}

export async function fetchPlacementDecisionContext(
  placementId: string,
  assignmentId?: string
): Promise<AcademicDecisionContext> {
  const sp = new URLSearchParams();
  if (assignmentId) sp.set("academic_assignment_id", assignmentId);

  const res = await fetch(`/api/bff/university/placements/${encodeURIComponent(placementId)}/conclusion-context?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_CONTEXT_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as AcademicDecisionContext;
}

export async function submitAcademicPlacementConclusion(
  placementId: string,
  payload: {
    decision: "ACADEMIC_REVIEW_COMPLETE" | "ACADEMIC_REVISION_REQUIRED";
    reason: string;
    academic_assignment_id?: string;
    terms_id?: string;
    version?: number;
    expected_basis_digest?: string;
  }
): Promise<{ ok: boolean; receipt?: Record<string, unknown> }> {
  const res = await fetch(`/api/bff/university/placements/${encodeURIComponent(placementId)}/conclude`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUBMIT_CONCLUSION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; receipt?: Record<string, unknown> };
}

export async function fetchCoordinatorAssignmentQueue(
  institutionId?: string
): Promise<{ items: CoordinatorAssignmentQueueItem[]; teachers: AcademicTeacherOption[]; institution_id?: string }> {
  const sp = new URLSearchParams();
  if (institutionId) sp.set("institution_id", institutionId);

  const res = await fetch(`/api/bff/university/assignment-queue?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_QUEUE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return {
    items: (data.items || []) as CoordinatorAssignmentQueueItem[],
    teachers: (data.teachers || []) as AcademicTeacherOption[],
    institution_id: data.institution_id,
  };
}

export async function assignTeacherToPlacement(
  placementId: string,
  payload: {
    institution_id: string;
    supervisor_id: string;
    supervision_id: string;
  }
): Promise<{ ok: boolean; assignment?: Record<string, unknown> }> {
  const res = await fetch(`/api/bff/university/placements/${encodeURIComponent(placementId)}/assign-teacher`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ASSIGN_TEACHER_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; assignment?: Record<string, unknown> };
}

export interface MentorReviewQueueItem {
  revision_id: string;
  daily_log_id: string;
  placement_id: string;
  organization_id: string;
  log_date: string | null;
  day_type: string;
  summary: string;
  total_minutes: number;
  status: string;
  submitted_at: string | null;
  due_at: string | null;
  is_escalated: boolean;
  candidate: {
    id: string;
    user_id: string;
    full_name: string;
    headline: string;
  };
}

export interface MentorLogRevisionDetail {
  contract_id: "API-091";
  revision_id: string;
  daily_log_id: string;
  placement_id: string;
  organization_id: string;
  log_date: string | null;
  day_type: string;
  summary: string;
  total_minutes: number;
  status: string;
  submitted_at: string | null;
  due_at: string | null;
  is_escalated: boolean;
  candidate: {
    id: string;
    user_id: string;
    full_name: string;
    headline: string;
  };
  terms?: {
    terms_id: string;
    daily_limit_minutes: number;
    weekly_limit_hours: number;
  } | null;
  tasks: Array<{
    task_id: string;
    title: string;
    minutes: number;
    start_minute?: number | null;
    end_minute?: number | null;
    evidence?: Array<{
      evidence_id: string;
      file_id: string;
      visibility: string;
      created_at?: string | null;
    }>;
  }>;
  existing_review?: {
    review_id: string;
    decision: string;
    comment?: string | null;
    decided_at?: string | null;
  } | null;
}

export interface MentorAssignmentItem {
  id: string;
  placement_id: string;
  membership_id: string;
  assigned_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
}

export interface OrganizationPlacementItem {
  id: string;
  application_id: string;
  offer_id: string;
  candidate_id: string;
  organization_id: string;
  enrollment_id?: string | null;
  academic_track: boolean;
  status: string;
  start_date: string;
  end_date: string;
  version: number;
  current_terms_id: string;
}

export async function fetchMentorReviewQueue(
  limit = 50,
  cursor?: string
): Promise<{ items: MentorReviewQueueItem[]; total: number; next_cursor: string | null }> {
  const sp = new URLSearchParams({ limit: limit.toString() });
  if (cursor) sp.set("cursor", cursor);

  const res = await fetch(`/api/bff/employer/mentor/review-queue?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_MENTOR_QUEUE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return {
    items: (data.items || []) as MentorReviewQueueItem[],
    total: data.total ?? (data.items || []).length,
    next_cursor: data.next_cursor || null,
  };
}

export async function fetchWorkplaceRevisionDetail(
  revisionId: string
): Promise<MentorLogRevisionDetail> {
  const res = await fetch(`/api/bff/employer/mentor/log-revisions/${encodeURIComponent(revisionId)}/workplace`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_WORKPLACE_REVISION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data.revision as MentorLogRevisionDetail;
}

export async function submitWorkplaceReview(
  revisionId: string,
  payload: {
    decision: "APPROVED" | "CHANGES_REQUESTED" | "REJECTED";
    comment?: string;
  }
): Promise<{ ok: boolean; review: Record<string, unknown> }> {
  const res = await fetch(`/api/bff/employer/mentor/log-revisions/${encodeURIComponent(revisionId)}/workplace-reviews`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUBMIT_WORKPLACE_REVIEW_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { ok: boolean; review: Record<string, unknown> };
}

export async function fetchMentorAssignments(
  limit = 50
): Promise<MentorAssignmentItem[]> {
  const res = await fetch(`/api/bff/employer/mentor/assignments?limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_MENTOR_ASSIGNMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as MentorAssignmentItem[];
}

export async function fetchOrganizationPlacements(
  orgId: string,
  limit = 50
): Promise<OrganizationPlacementItem[]> {
  const res = await fetch(`/api/bff/employer/placements?organization_id=${encodeURIComponent(orgId)}&limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ORG_PLACEMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as OrganizationPlacementItem[];
}

// ---------------------------------------------------------------------------
// Candidate Offer Acceptance, Dual-Confirmed Job Engagements & Placements Hub (FB-164)
// ---------------------------------------------------------------------------

export interface OfferRespondPayload {
  decision: "ACCEPT" | "DECLINE";
  note?: string;
}

export interface OfferRespondResponse {
  contract_id: string;
  id: string;
  status: string;
  accepted_at?: string;
  opportunity_id?: string;
  vacancies_remaining?: number;
  engagement_id?: string;
  message: string;
}

export interface JobEngagementConfirmation {
  id: string;
  side: "CANDIDATE" | "EMPLOYER";
  action: "CONFIRM_START" | "CONFIRM_END" | "DISPUTE_START" | "DISPUTE_END";
  response: string;
  occurred_at: string;
}

export interface JobEngagementDetail {
  contract_id: string;
  id: string;
  application_id: string;
  offer_id: string;
  status: "PENDING_START_CONFIRMATION" | "ACTIVE" | "COMPLETED" | "DISPUTED";
  start_date: string | null;
  end_date: string | null;
  terms_snapshot: Record<string, unknown>;
  confirmed_started_at: string | null;
  my_side: "CANDIDATE" | "EMPLOYER";
  opportunity: {
    id: string;
    organization_id: string;
    kind: string;
    status: string;
  };
  confirmations: JobEngagementConfirmation[];
  pending_sides: string[];
}

export interface EngagementConfirmationPayload {
  action: "CONFIRM_START" | "CONFIRM_END" | "DISPUTE_START" | "DISPUTE_END";
  note?: string;
}

export interface PlacementPlanTask {
  code: string;
  title: string;
  expected_result: string;
  required: boolean;
  target_minutes?: number | null;
}

export interface PlacementPlanDetail {
  contract_id: string;
  placement_id: string;
  status: string;
  terms_id: string;
  version: number;
  start_date: string;
  end_date: string;
  academic_required: boolean;
  academic_scope: Record<string, unknown>;
  title?: string;
  objectives?: string;
  daily_limit_minutes: number;
  weekly_limit_minutes: number;
  required_minutes: number;
  tasks: PlacementPlanTask[];
}

export interface PlacementAcceptPayload {
  terms_id: string;
  version: number;
  idempotency_key?: string;
}

export async function respondToCandidateOffer(
  offerId: string,
  payload: OfferRespondPayload
): Promise<OfferRespondResponse> {
  const res = await fetch(`/api/bff/candidate/offers/${encodeURIComponent(offerId)}/respond`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "RESPOND_TO_OFFER_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OfferRespondResponse;
}

export async function fetchCandidateEngagement(
  engagementId: string
): Promise<JobEngagementDetail> {
  const res = await fetch(`/api/bff/candidate/engagements/${encodeURIComponent(engagementId)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ENGAGEMENT_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as JobEngagementDetail;
}

export async function submitEngagementConfirmation(
  engagementId: string,
  payload: EngagementConfirmationPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/candidate/engagements/${encodeURIComponent(engagementId)}/confirmations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUBMIT_ENGAGEMENT_CONFIRMATION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

export async function fetchCandidatePlacementsList(
  limit = 50,
  after?: string
): Promise<{ contract_id: string; items: CandidatePlacementItem[]; next_after: string | null }> {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  if (after) query.set("after", after);
  const res = await fetch(`/api/bff/candidate/placements?${query.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_CANDIDATE_PLACEMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { contract_id: string; items: CandidatePlacementItem[]; next_after: string | null };
}

export async function fetchPlacementPlanDetail(
  placementId: string
): Promise<PlacementPlanDetail> {
  const res = await fetch(`/api/bff/candidate/placements/${encodeURIComponent(placementId)}/plan`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_PLACEMENT_PLAN_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as PlacementPlanDetail;
}

export async function acceptCandidatePlacementTerms(
  placementId: string,
  payload: PlacementAcceptPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/candidate/placements/${encodeURIComponent(placementId)}/accept`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ACCEPT_PLACEMENT_TERMS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Candidate Ratings, Reviews, Double-Blind & Appeals Types & Methods (API-057, API-047, API-058)
// ---------------------------------------------------------------------------

export interface RatingAggregate {
  sample_size: number;
  score: number | null;
  score_status: "UNRATED" | "WITHHELD_INSUFFICIENT_SAMPLE" | "PUBLISHED" | "COMPUTATION_PENDING" | string;
  explanation: string;
  window_start?: string | null;
  window_end?: string | null;
  computed_at?: string | null;
  rubric_id?: string | null;
}

export interface RatingCriterion {
  id: string;
  code: string;
  title: string;
  weight: number;
  required: boolean;
}

export interface RubricVersion {
  id: string;
  family: string;
  version: number;
  scale_min: number;
  scale_max: number;
  criteria: RatingCriterion[];
}

export interface ReceivedRatingItem {
  id: string;
  rubric_id: string;
  status: string;
  blind_window_active: boolean;
  publish_after?: string | null;
  comment?: string | null;
  rater_id?: string | null;
  message?: string;
  submitted_at?: string | null;
  placement_id?: string | null;
  engagement_id?: string | null;
}

export interface GivenRatingItem {
  id: string;
  rubric_id: string;
  placement_id?: string | null;
  engagement_id?: string | null;
  target_user_id?: string | null;
  target_org_id?: string | null;
  version?: number;
  status: string;
  comment?: string | null;
  submitted_at?: string | null;
  publish_after?: string | null;
}

export interface EligibleRelationItem {
  relation_type: "PLACEMENT" | "ENGAGEMENT" | string;
  relation_id: string;
  role: string;
  status: string;
  organization_id?: string;
  start_date?: string | null;
  end_date?: string | null;
}

export interface CandidateRatingsResponse {
  contract_id: string;
  target_user_id: string;
  feature_enabled: boolean;
  feature_flag: string;
  aggregate: RatingAggregate;
  submissions_received: ReceivedRatingItem[];
  submissions_given: GivenRatingItem[];
  eligible_relations: EligibleRelationItem[];
  available_rubrics: RubricVersion[];
}

export interface SubmitRatingPayload {
  scores: { criterion_id: string; score: number }[];
  rubric_id?: string;
  comment?: string;
  idempotency_key?: string;
}

export interface RatingAppealPayload {
  reason: string;
  category?: string;
  evidence_notes?: string;
}

export async function fetchCandidateRatings(): Promise<CandidateRatingsResponse> {
  const res = await fetch("/api/bff/candidate/ratings", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_RATINGS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateRatingsResponse;
}

export async function submitEngagementRating(
  engagementId: string,
  payload: SubmitRatingPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/candidate/engagements/${encodeURIComponent(engagementId)}/ratings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUBMIT_RATING_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

export async function submitRatingAppeal(
  ratingId: string,
  payload: RatingAppealPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/candidate/ratings/${encodeURIComponent(ratingId)}/appeals`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SUBMIT_APPEAL_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Candidate Saved Opportunities Types & Methods (API-004, API-037, API-038)
// ---------------------------------------------------------------------------

export interface SavedOpportunityItem {
  id: string;
  candidate_id: string;
  opportunity_id: string;
  created_at?: string | null;
  opportunity: {
    id: string;
    organization_id?: string;
    kind: string;
    status: string;
    is_closed: boolean;
    closed_at?: string | null;
    published_at?: string | null;
    current_revision_id?: string;
    title?: string;
    work_mode?: string;
    contract_type?: string;
    is_paid?: boolean;
  };
}

export interface SavedOpportunitiesListResponse {
  items: SavedOpportunityItem[];
  total: number;
  page: number;
  page_size: number;
}

export const fetchSavedOpportunities = fetchMySavedOpportunities;

// ---------------------------------------------------------------------------
// Employer Organization, Team & Verification Types & Methods (API-072, API-073, API-074, API-075, API-067)
// ---------------------------------------------------------------------------

export interface OrgCapabilityItem {
  id?: string;
  capability: "JOB_EMPLOYER" | "INTERNSHIP_HOST" | string;
  status: "ACTIVE" | "VERIFIED" | "PENDING" | "NOT_REQUESTED" | string;
  created_at?: string;
  updated_at?: string;
}

export interface OrgMembershipItem {
  id: string;
  organization_id: string;
  user_id: string;
  status: "ACTIVE" | "PENDING_APPROVAL" | "REVOKED" | string;
  created_at?: string;
  updated_at?: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
  role?: string;
}

export interface OrgVerificationCaseItem {
  id: string;
  kind: string;
  status: string;
  created_at?: string;
  due_at?: string;
  decision_reason?: string | null;
}

export interface OrgVerificationStatusResponse {
  contract_id: string;
  organization_id: string;
  membership_id: string;
  membership_status: string;
  status?: string;
  cases: OrgVerificationCaseItem[];
  capabilities: OrgCapabilityItem[];
}

export interface InviteMemberPayload {
  channel: "EMAIL" | "PHONE";
  destination: string;
  role_code: "HR" | "HOST_COORDINATOR" | "MENTOR" | "BILLING";
}

export interface RevokeMembershipPayload {
  reason: string;
}

export async function fetchOrgCapabilities(
  orgId: string
): Promise<{ contract_id: string; items: OrgCapabilityItem[] }> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/capabilities`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ORG_CAPABILITIES_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { contract_id: string; items: OrgCapabilityItem[] };
}

export async function fetchOrgMemberships(
  orgId: string
): Promise<{ contract_id: string; organization_id: string; items: OrgMembershipItem[] }> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/memberships`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ORG_MEMBERSHIPS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as { contract_id: string; organization_id: string; items: OrgMembershipItem[] };
}

export async function inviteOrgMember(
  orgId: string,
  payload: InviteMemberPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/invitations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "INVITE_ORG_MEMBER_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

export async function revokeOrgMembership(
  orgId: string,
  membershipId: string,
  payload: RevokeMembershipPayload
): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/memberships/${encodeURIComponent(membershipId)}/revoke`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "REVOKE_ORG_MEMBERSHIP_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as Record<string, unknown>;
}

export async function fetchOrgVerificationStatus(
  orgId: string
): Promise<OrgVerificationStatusResponse> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(orgId)}/verification`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ORG_VERIFICATION_STATUS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OrgVerificationStatusResponse;
}

// ---------------------------------------------------------------------------
// FB-170: University Report Exports, Supervisions & Agreements (API-100, 098, 101)
// ---------------------------------------------------------------------------
export interface InstitutionExportSummary {
  institution_id: string;
  institution_name: string;
  registry_code?: string;
  total_students_enrolled: number;
  total_supervisions: number;
  total_active_agreements: number;
  total_placements: number;
  placements_by_status: Record<string, number>;
  total_submitted_logs: number;
  total_logged_minutes: number;
  total_logged_hours: number;
  total_academic_conclusions: number;
  placements?: Array<Record<string, unknown>>;
  generated_at: string;
  disclaimer: string;
}

export interface InstitutionExportReceipt {
  contract_id: string;
  capability: string;
  export_id: string;
  institution_id: string;
  file_id: string;
  actor_role: string;
  export_format: "PDF" | "JSON";
  created_at: string;
  expires_at: string;
  download_url: string;
  disclaimer: string;
  summary: InstitutionExportSummary;
  is_idempotent_replay: boolean;
}

export interface StudentSupervisionItem {
  id: string;
  enrollment_id: string;
  agreement_id: string;
  purpose: string;
  legal_basis?: string;
  status?: string;
  created_at?: string;
}

export interface AcademicAgreementItem {
  id: string;
  institution_id: string;
  organization_id: string;
  status: string;
  created_at?: string;
}

export async function generateInstitutionExport(
  institutionId: string,
  payload: { format: "PDF" | "JSON"; include_details?: boolean; idempotency_key?: string }
): Promise<InstitutionExportReceipt> {
  const res = await fetch(`/api/bff/university/institutions/${encodeURIComponent(institutionId)}/exports`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "GENERATE_EXPORT_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as InstitutionExportReceipt;
}

export async function fetchInstitutionSupervisions(
  institutionId: string,
  limit = 50
): Promise<StudentSupervisionItem[]> {
  const res = await fetch(`/api/bff/university/institutions/${encodeURIComponent(institutionId)}/supervisions?limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_SUPERVISIONS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as StudentSupervisionItem[];
}

export async function fetchInstitutionAcademicAgreements(
  institutionId: string,
  limit = 50
): Promise<AcademicAgreementItem[]> {
  const res = await fetch(`/api/bff/university/institutions/${encodeURIComponent(institutionId)}/agreements?limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_AGREEMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as AcademicAgreementItem[];
}

// ---------------------------------------------------------------------------
// FB-174: Employer Billing, Entitlements, Orders & Refunds (API-070, 093, 094, 095)
// ---------------------------------------------------------------------------

export interface OrgEntitlementUsage {
  concurrent_active_opportunities: number;
  concurrent_active_limit: number;
  concurrent_slots_available: number;
  quota_remaining: number | null;
  days_remaining: number;
}

export interface OrgActiveEntitlement {
  id: string;
  order_id: string | null;
  service_kind: string;
  plan_code: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  days_remaining: number;
  quota: number | null;
  post_credits_remaining: number | null;
  concurrent_active_limit: number;
  concurrent_active_count: number;
  concurrent_slots_remaining: number;
  created_at: string | null;
}

export interface OrgEntitlementsResponse {
  ok: boolean;
  contract_id: "API-070";
  organization_id: string;
  has_active_entitlement: boolean;
  active_entitlement: OrgActiveEntitlement | null;
  usage: OrgEntitlementUsage;
}

export interface OrgBillingPlan {
  code: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  quota: number | null;
  concurrent_active_limit: number;
}

export interface OrgOrderItem {
  id: string;
  amount: number;
  currency: string;
  status: string;
  plan_code?: string | null;
  price_snapshot?: Record<string, unknown> | null;
  created_at: string | null;
}

export interface OrgInvoiceItem {
  id: string;
  order_id: string;
  number: string;
  amount: number;
  currency: string;
  fiscal_status: string;
  status: string;
  issued_at: string | null;
  paid_at: string | null;
}

export interface OrgBillingOverviewResponse {
  ok: boolean;
  contract_id: "API-093";
  organization_id: string;
  plan: OrgBillingPlan;
  entitlement?: Record<string, unknown> | null;
  orders: OrgOrderItem[];
  invoices: OrgInvoiceItem[];
}

export interface CreateOrgOrderPayload {
  plan_code: string;
  idempotency_key?: string;
}

export interface OrgOrderResult {
  ok: boolean;
  contract_id: "API-094";
  order: OrgOrderItem;
  invoice: OrgInvoiceItem;
}

export interface RequestOrderRefundPayload {
  amount_uzs: number;
  reason: string;
}

export interface OrderRefundResult {
  ok: boolean;
  contract_id: "API-095";
  refund_id: string;
  status: string;
}

export async function fetchOrgEntitlements(
  organizationId: string
): Promise<OrgEntitlementsResponse> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(organizationId)}/entitlements`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_ENTITLEMENTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OrgEntitlementsResponse;
}

export async function fetchOrgBillingOverview(
  organizationId: string
): Promise<OrgBillingOverviewResponse> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(organizationId)}/billing`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_BILLING_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OrgBillingOverviewResponse;
}

export async function createOrgOrder(
  organizationId: string,
  payload: CreateOrgOrderPayload
): Promise<OrgOrderResult> {
  const res = await fetch(`/api/bff/employer/organization/${encodeURIComponent(organizationId)}/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "CREATE_ORDER_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OrgOrderResult;
}

export async function requestOrderRefund(
  orderId: string,
  payload: RequestOrderRefundPayload
): Promise<OrderRefundResult> {
  const res = await fetch(`/api/bff/employer/orders/${encodeURIComponent(orderId)}/refund`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "REQUEST_REFUND_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OrderRefundResult;
}

// ---------------------------------------------------------------------------
// FB-176: Operator Finance Summary, Reconciliation & Refunds (API-117, 115, 078)
// ---------------------------------------------------------------------------

export interface OperatorFinancePlanStat {
  plan_code: string;
  total_entitlements: number;
  active_count: number;
  cash_received_uzs: number;
  recognized_revenue_uzs: number;
  deferred_revenue_uzs: number;
}

export interface OperatorFinanceSummaryResponse {
  ok: boolean;
  contract_id: string;
  capability?: string;
  period?: {
    start_date: string | null;
    end_date: string | null;
  };
  cash_received_uzs?: number;
  cash_collected_uzs?: number;
  recognized_revenue_uzs?: number;
  deferred_revenue_uzs?: number;
  refunded_amount_uzs?: number;
  net_revenue_uzs?: number;
  active_subscriptions_count?: number;
  plans_breakdown?: OperatorFinancePlanStat[];
  currency?: string;
}

export interface OperatorReconciliationItem {
  ledger_entry_id?: string;
  id?: string;
  occurred_at?: string | null;
  entry_kind?: string;
  organization_id?: string | null;
  order_id?: string | null;
  payment_attempt_id?: string | null;
  refund_id?: string | null;
  provider?: string | null;
  provider_transaction_id?: string | null;
  ledger_amount_uzs?: number;
  gateway_amount_uzs?: number | null;
  currency?: string;
  ledger_status?: string;
  gateway_status?: string | null;
  is_discrepant?: boolean;
  discrepancy_flags?: string[];
  created_at?: string;
}

export interface OperatorReconciliationSummary {
  total_reconciled?: number;
  total_discrepancies?: number;
  matched_count?: number;
  total_checked?: number;
}

export interface OperatorReconciliationResponse {
  ok: boolean;
  contract_id: string;
  capability?: string;
  items: OperatorReconciliationItem[];
  summary?: OperatorReconciliationSummary;
  next_cursor?: string | null;
  has_more?: boolean;
  total_records?: number;
}

export interface ApproveOperatorRefundResult {
  ok: boolean;
  contract_id: "API-078";
  refund_id: string;
  status: "PENDING_SECOND_APPROVAL" | "APPROVED";
}

export async function fetchOperatorFinanceSummary(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<OperatorFinanceSummaryResponse> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);

  const res = await fetch(`/api/bff/operator/finance-summary?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_FINANCE_SUMMARY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorFinanceSummaryResponse;
}

export async function fetchOperatorReconciliation(params?: {
  start_date?: string;
  end_date?: string;
  provider?: string;
  discrepancy_only?: boolean;
  limit?: number;
  cursor?: string;
}): Promise<OperatorReconciliationResponse> {
  const search = new URLSearchParams();
  if (params?.start_date) search.set("start_date", params.start_date);
  if (params?.end_date) search.set("end_date", params.end_date);
  if (params?.provider) search.set("provider", params.provider);
  if (params?.discrepancy_only !== undefined) search.set("discrepancy_only", String(params.discrepancy_only));
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.cursor) search.set("cursor", params.cursor);

  const res = await fetch(`/api/bff/operator/reconciliation?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_RECONCILIATION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as OperatorReconciliationResponse;
}

export async function approveOperatorRefund(
  refundId: string
): Promise<ApproveOperatorRefundResult> {
  const res = await fetch(`/api/bff/operator/refunds/${encodeURIComponent(refundId)}/approve`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "APPROVE_REFUND_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as ApproveOperatorRefundResult;
}

// ---------------------------------------------------------------------------
// FB-178: Customer Support, Privacy Rights & Notification Preferences
// ---------------------------------------------------------------------------

export interface CustomerSupportTicketItem {
  id: string;
  ticket_number?: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  created_at: string;
  updated_at?: string;
  messages_count?: number;
}

export interface CustomerSupportMessageItem {
  id: string;
  ticket_id: string;
  sender_user_id: string;
  body: string;
  file_id?: string | null;
  internal?: boolean;
  created_at: string;
}

export interface CreateSupportTicketPayload {
  subject: string;
  body: string;
  category?: string;
  priority?: string;
  file_id?: string | null;
}

export interface CustomerSupportTicketsResponse {
  ok: boolean;
  contract_id: "API-063";
  items: CustomerSupportTicketItem[];
  page: number;
  page_size: number;
  total?: number;
}

export interface CustomerSupportMessagesResponse {
  ok: boolean;
  contract_id: "API-064";
  items: CustomerSupportMessageItem[];
  messages?: CustomerSupportMessageItem[];
  total_messages?: number;
  page?: number;
  page_size?: number;
  total?: number;
}

export interface CustomerPrivacyRequestItem {
  id: string;
  user_id: string;
  kind: "EXPORT" | "DELETE" | "RECTIFY" | string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "RESOLVED" | "REJECTED" | string;
  reason?: string | null;
  resolution_reason?: string | null;
  result_file_id?: string | null;
  created_at: string;
  updated_at?: string;
  resolved_at?: string | null;
}

export interface CustomerPrivacyRequestsResponse {
  ok: boolean;
  contract_id: "API-062";
  items: CustomerPrivacyRequestItem[];
  page?: number;
  page_size?: number;
  total?: number;
}

export interface NotificationPreferenceItem {
  id?: string;
  channel: "EMAIL" | "SMS" | "PUSH" | string;
  purpose: "SECURITY" | "TRANSACTIONAL" | "MARKETING" | "OPPORTUNITIES" | string;
  enabled: boolean;
  updated_at?: string;
}

export interface NotificationPreferencesResponse {
  ok: boolean;
  contract_id: "API-059";
  preferences: NotificationPreferenceItem[];
  user_id?: string;
}

export async function fetchMySupportTickets(params?: {
  status?: string;
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<CustomerSupportTicketsResponse> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.category) search.set("category", params.category);
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));

  const res = await fetch(`/api/bff/me/support-tickets?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_MY_TICKETS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CustomerSupportTicketsResponse;
}

export async function createSupportTicket(
  payload: CreateSupportTicketPayload
): Promise<{ ok: boolean; contract_id: string; ticket_id: string; status: string }> {
  const res = await fetch(`/api/bff/me/support-tickets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "CREATE_TICKET_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchSupportTicketMessages(
  ticketId: string,
  params?: { page?: number; page_size?: number }
): Promise<CustomerSupportMessagesResponse> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));

  const res = await fetch(`/api/bff/support-tickets/${encodeURIComponent(ticketId)}/messages?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_MESSAGES_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CustomerSupportMessagesResponse;
}

export async function postCustomerSupportMessage(
  ticketId: string,
  payload: { body: string; file_id?: string | null }
): Promise<{ ok: boolean; contract_id: string; message_id: string }> {
  const res = await fetch(`/api/bff/support-tickets/${encodeURIComponent(ticketId)}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "POST_MESSAGE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchMyPrivacyRequests(params?: {
  kind?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<CustomerPrivacyRequestsResponse> {
  const search = new URLSearchParams();
  if (params?.kind) search.set("kind", params.kind);
  if (params?.status) search.set("status", params.status);
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));

  const res = await fetch(`/api/bff/me/privacy-requests?${search.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_PRIVACY_REQUESTS_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CustomerPrivacyRequestsResponse;
}

export async function createPrivacyRequest(payload: {
  kind: "EXPORT" | "DELETE" | "RECTIFY";
  reason?: string;
  details?: Record<string, unknown>;
}): Promise<{ ok: boolean; contract_id: string; request_id: string; status: string }> {
  const res = await fetch(`/api/bff/me/privacy-requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "CREATE_PRIVACY_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function resolveOperatorPrivacyRequest(
  requestId: string,
  payload: { status: "RESOLVED" | "COMPLETED" | "REJECTED"; reason: string; result_file_id?: string | null }
): Promise<{ ok: boolean; contract_id: string; request_id: string; status: string }> {
  const res = await fetch(`/api/bff/operator/privacy-requests/${encodeURIComponent(requestId)}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "RESOLVE_PRIVACY_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchMyNotificationPreferences(): Promise<NotificationPreferencesResponse> {
  const res = await fetch(`/api/bff/me/notification-preferences`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "FETCH_PREFERENCES_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as NotificationPreferencesResponse;
}

export async function updateMyNotificationPreferences(
  preferences: NotificationPreferenceItem[]
): Promise<NotificationPreferencesResponse> {
  const res = await fetch(`/api/bff/me/notification-preferences`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ preferences }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "UPDATE_PREFERENCES_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as NotificationPreferencesResponse;
}

// ---------------------------------------------------------------------------
// FB-180: Opportunity Lifecycle & Interview Responses (API-081, API-082, API-042)
// ---------------------------------------------------------------------------

export interface PublishOpportunityResponse {
  ok: boolean;
  contract_id: "API-081";
  opportunity_id?: string;
  status: string;
  [key: string]: unknown;
}

export interface TransitionOpportunityResponse {
  ok: boolean;
  contract_id: "API-082";
  opportunity_id?: string;
  status: "PAUSED" | "CLOSED" | string;
  [key: string]: unknown;
}

export interface InterviewResponsePayload {
  response: "ACCEPTED" | "DECLINED" | "RESCHEDULE_REQUESTED" | "COMPLETED" | "NO_SHOW";
  note?: string | null;
}

export interface InterviewResponseResult {
  ok: boolean;
  contract_id: "API-042";
  interview_id?: string;
  response?: string;
  status?: string;
  [key: string]: unknown;
}

export async function publishEmployerOpportunity(
  opportunityId: string
): Promise<PublishOpportunityResponse> {
  const res = await fetch(`/api/bff/employer/opportunities/${encodeURIComponent(opportunityId)}/publish`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "PUBLISH_OPPORTUNITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as PublishOpportunityResponse;
}

export async function transitionOpportunityStatus(
  opportunityId: string,
  status: "PAUSED" | "CLOSED"
): Promise<TransitionOpportunityResponse> {
  const res = await fetch(`/api/bff/employer/opportunities/${encodeURIComponent(opportunityId)}/transition`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ status }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "TRANSITION_OPPORTUNITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as TransitionOpportunityResponse;
}

export async function respondToInterview(
  interviewId: string,
  payload: InterviewResponsePayload
): Promise<InterviewResponseResult> {
  const res = await fetch(`/api/bff/candidate/interviews/${encodeURIComponent(interviewId)}/responses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "RESPOND_INTERVIEW_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as InterviewResponseResult;
}

// -------------------------------------------------------------------------
// Candidate Saved Opportunities (API-004, API-037, API-038) & Notifications (API-031)
// -------------------------------------------------------------------------

export interface SavedOpportunitiesResponse {
  ok: boolean;
  contract_id: string;
  items: SavedOpportunityItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SaveOpportunityResult {
  ok: boolean;
  contract_id: string;
  saved: boolean;
  opportunity_id: string;
  id?: string | null;
}

export interface NotificationItem {
  id: string;
  created_at: string;
  template_code: string;
  placement_id?: string | null;
  read_at?: string | null;
  opportunity_id?: string | null;
  application_id?: string | null;
  ticket_id?: string | null;
  is_read: boolean;
  notice?: Record<string, unknown> | null;
}

export interface NotificationsResponse {
  ok: boolean;
  contract_id: string;
  items: NotificationItem[];
  next_after?: string | null;
}

export async function fetchMySavedOpportunities(
  page: number = 1,
  pageSize: number = 20
): Promise<SavedOpportunitiesResponse> {
  const res = await fetch(`/api/bff/me/saved-opportunities?page=${page}&page_size=${pageSize}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SAVED_OPPORTUNITIES_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as SavedOpportunitiesResponse;
}

export async function saveOpportunity(
  opportunityId: string,
  toggle: boolean = false
): Promise<SaveOpportunityResult> {
  const res = await fetch("/api/bff/me/saved-opportunities", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ opportunity_id: opportunityId, toggle }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SAVE_OPPORTUNITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as SaveOpportunityResult;
}

export async function deleteSavedOpportunity(
  identifier: string
): Promise<{ ok: boolean; contract_id: string; deleted_id: string }> {
  const res = await fetch(`/api/bff/me/saved-opportunities/${encodeURIComponent(identifier)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "DELETE_SAVED_OPPORTUNITY_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchMyNotifications(
  unreadOnly: boolean = false,
  limit: number = 50,
  after?: string
): Promise<NotificationsResponse> {
  let query = `limit=${limit}&unread_only=${unreadOnly}`;
  if (after) query += `&after=${encodeURIComponent(after)}`;
  const res = await fetch(`/api/bff/me/notifications?${query}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "NOTIFICATIONS_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as NotificationsResponse;
}

export async function markNotificationRead(
  notificationId: string
): Promise<{ ok: boolean; contract_id: string; id: string; read_at: string }> {
  const res = await fetch(`/api/bff/me/notifications/${encodeURIComponent(notificationId)}/read`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "MARK_NOTIFICATION_READ_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

// ---------------------------------------------------------------------------
// FB-184: Student Academic Enrollments (HEMIS) & Availability Exceptions
// Canonical Contracts: API-027, API-034, API-036
// ---------------------------------------------------------------------------

export interface CandidateEnrollmentItem {
  id: string;
  candidate_id?: string;
  institution_id: string;
  institution_name?: string;
  program: string;
  start_date: string;
  end_date?: string | null;
  student_ref?: string | null;
  current_student: boolean;
  reviewed: boolean;
  status: string;
  created_at?: string;
}

export interface CandidateEnrollmentsResponse {
  ok: boolean;
  contract_id?: string;
  items: CandidateEnrollmentItem[];
  next_cursor?: string | null;
}

export interface CreateEnrollmentPayload {
  institution_id: string;
  program: string;
  start_date: string;
  end_date?: string | null;
  student_ref?: string | null;
  evidence_note?: string;
  file_ids?: string[];
  idempotency_key?: string;
}

export interface EndEnrollmentPayload {
  reason: string;
  effective_end_date?: string | null;
  idempotency_key?: string;
}

export interface AvailabilityExceptionItem {
  local_date: string;
  kind: "AVAILABLE" | "UNAVAILABLE";
  start_minute: number;
  end_minute: number;
}

export interface SaveAvailabilityExceptionsPayload {
  from_date: string;
  to_date: string;
  exceptions: AvailabilityExceptionItem[];
}

export interface VerifiedInstitutionItem {
  id: string;
  name: string;
  registry_code: string;
  region: string;
}

export async function fetchCandidateEnrollments(
  limit: number = 50,
  afterId?: string
): Promise<CandidateEnrollmentItem[]> {
  const sp = new URLSearchParams();
  sp.set("limit", limit.toString());
  if (afterId) sp.set("after_id", afterId);

  const res = await fetch(`/api/bff/candidate/enrollments?${sp.toString()}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ENROLLMENTS_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as CandidateEnrollmentItem[];
}

export async function createCandidateEnrollment(
  payload: CreateEnrollmentPayload
): Promise<{ ok: boolean; contract_id?: string; id?: string; enrollment_id?: string; status?: string }> {
  const res = await fetch("/api/bff/candidate/enrollments", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ENROLLMENT_CREATE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchCandidateEnrollmentDetail(
  id: string
): Promise<CandidateEnrollmentItem> {
  const res = await fetch(`/api/bff/candidate/enrollments/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ENROLLMENT_DETAIL_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CandidateEnrollmentItem;
}

export async function endCandidateEnrollment(
  id: string,
  payload: EndEnrollmentPayload
): Promise<{ ok: boolean; status?: string }> {
  const res = await fetch(`/api/bff/candidate/enrollments/${encodeURIComponent(id)}/end`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "ENROLLMENT_END_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

export async function fetchVerifiedInstitutions(): Promise<VerifiedInstitutionItem[]> {
  const res = await fetch("/api/bff/candidate/institutions", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "INSTITUTIONS_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return (data.items || []) as VerifiedInstitutionItem[];
}

export async function saveCandidateAvailabilityExceptions(
  payload: SaveAvailabilityExceptionsPayload
): Promise<{ ok: boolean; contract_id?: string }> {
  const res = await fetch("/api/bff/candidate/availability/exceptions", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "AVAILABILITY_EXCEPTIONS_SAVE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data;
}

// ---------------------------------------------------------------------------
// Candidate & User Security, MFA & Sessions Hub (API-060, API-061)
// ---------------------------------------------------------------------------

export interface ActiveSessionItem {
  id: string;
  created_at: string;
  expires_at: string;
  last_seen_at?: string;
  assurance: string; // 'PASSWORD' | 'MFA'
  is_current: boolean;
}

export interface UserSecurityOverview {
  ok: boolean;
  user_id: string;
  totp_enabled: boolean;
  recovery_codes_count: number;
  current_session_id: string;
  sessions: ActiveSessionItem[];
  contract_id?: string;
}

export interface EnableTotpResult {
  ok: boolean;
  totp_enabled: boolean;
  enrollment_pending: boolean;
  secret: string;
  contract_id?: string;
}

export interface DisableTotpResult {
  ok: boolean;
  totp_enabled: boolean;
  step_up_verified: boolean;
  reauthentication_required: boolean;
  contract_id?: string;
}

export interface ConfirmTotpResult {
  ok: boolean;
  totp_enabled: boolean;
  reauthentication_required: boolean;
  contract_id?: string;
}

export interface RecoveryCodesResult {
  ok: boolean;
  recovery_codes: string[];
  show_once: boolean;
  contract_id?: string;
}

export interface RevokeSessionResult {
  ok: boolean;
  session_id: string;
  status: string;
  revoked_at: string;
  contract_id?: string;
}

export async function fetchUserSecurityOverview(): Promise<UserSecurityOverview> {
  const res = await fetch("/api/bff/me/security", {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "SECURITY_OVERVIEW_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as UserSecurityOverview;
}

export async function requestTotpEnrollment(
  currentPassword: string,
  stepUpTotpCode?: string
): Promise<EnableTotpResult> {
  const payload: Record<string, unknown> = {
    enable_totp: true,
    current_password: currentPassword,
  };
  if (stepUpTotpCode) payload.step_up_totp_code = stepUpTotpCode;

  const res = await fetch("/api/bff/me/security", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "TOTP_ENROLLMENT_REQUEST_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as EnableTotpResult;
}

export async function confirmTotpEnrollment(code: string): Promise<ConfirmTotpResult> {
  const res = await fetch("/api/bff/me/security/totp/confirm", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "TOTP_CONFIRMATION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as ConfirmTotpResult;
}

export async function disableTotp(
  currentPassword: string,
  stepUpTotpCode?: string
): Promise<DisableTotpResult> {
  const payload: Record<string, unknown> = {
    enable_totp: false,
    current_password: currentPassword,
  };
  if (stepUpTotpCode) payload.step_up_totp_code = stepUpTotpCode;

  const res = await fetch("/api/bff/me/security", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "TOTP_DISABLE_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as DisableTotpResult;
}

export async function generateRecoveryCodes(
  currentPassword: string,
  totpCode?: string
): Promise<RecoveryCodesResult> {
  const payload: Record<string, unknown> = {
    current_password: currentPassword,
  };
  if (totpCode) payload.totp_code = totpCode;

  const res = await fetch("/api/bff/me/security/recovery-codes", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "RECOVERY_CODES_GENERATION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as RecoveryCodesResult;
}

export async function revokeUserSession(sessionId: string): Promise<RevokeSessionResult> {
  const res = await fetch(`/api/bff/me/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "REVOKE_SESSION_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as RevokeSessionResult;
}

// ---------------------------------------------------------------------------
// Public CMS: Policies & Help Documentation (API-013, API-014)
// ---------------------------------------------------------------------------

export interface PolicyClauseItem {
  id: string;
  title: string;
  summary: string;
}

export interface PolicyDocumentResponse {
  ok: boolean;
  contract_id: string;
  document: string;
  title: string;
  version: string;
  effective_date: string;
  contact_email: string;
  content_markdown: string;
  clauses: PolicyClauseItem[];
}

export interface HelpSectionItem {
  heading: string;
  anchor: string;
}

export interface HelpDocumentResponse {
  ok: boolean;
  contract_id: string;
  slug: string;
  title: string;
  version: string;
  effective_date: string;
  content_markdown: string;
  sections: HelpSectionItem[];
}

export async function fetchPublicPolicy(document: string): Promise<PolicyDocumentResponse> {
  const res = await fetch(`/api/bff/public/policies/${encodeURIComponent(document.toLowerCase())}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "POLICY_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as PolicyDocumentResponse;
}

export async function fetchPublicHelp(document: string): Promise<HelpDocumentResponse> {
  const res = await fetch(`/api/bff/public/help/${encodeURIComponent(document.toLowerCase())}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.error || "HELP_FETCH_FAILED");
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as HelpDocumentResponse;
}

// ---------------------------------------------------------------------------
// Standalone Auth & Onboarding Registration API (FB-190)
// ---------------------------------------------------------------------------

export interface AuthOptionsResponse {
  ok: boolean;
  channels: string[];
  otp_expires_in: number;
  otp_max_attempts: number;
  resend_after: number;
  terms_version: string;
  privacy_version: string;
}

export interface ChallengeIssueResponse {
  ok: boolean;
  challenge_id: string;
  status: string;
  expires_in: number;
  resend_after: number;
}

export interface ChallengeConsumeResponse {
  ok: boolean;
  verification_token: string;
  purpose: string;
  expires_in: number;
}

export interface RegisterUserPayload {
  verification_token: string;
  display_name: string;
  password: string;
  adult_confirmed: boolean;
  terms_version?: string;
  privacy_version?: string;
  roles?: string[];
  enable_totp?: boolean;
}

export interface RegisterUserResponse {
  ok: boolean;
  user: {
    id: string;
    display_name: string;
    roles: string[];
    adult_declared_at: string;
  };
  logged_in: boolean;
}

export async function fetchAuthOptions(): Promise<AuthOptionsResponse> {
  const res = await fetch("/api/bff/auth/options", {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || data.error || "OPTIONS_FETCH_FAILED");
  }
  return data as AuthOptionsResponse;
}

export async function issueAuthChallenge(
  channel: "PHONE" | "EMAIL",
  destination: string,
  purpose: "REGISTER" | "LOGIN" | "RECOVERY"
): Promise<ChallengeIssueResponse> {
  const res = await fetch("/api/bff/auth/challenges", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ channel, destination, purpose }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || data.error || "CHALLENGE_FAILED");
  }
  return data as ChallengeIssueResponse;
}

export async function consumeAuthChallenge(
  challenge_id: string,
  purpose: "REGISTER" | "LOGIN" | "RECOVERY",
  code: string
): Promise<ChallengeConsumeResponse> {
  const res = await fetch(`/api/bff/auth/challenges/${encodeURIComponent(challenge_id)}/consume`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ purpose, code }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || data.error || "CODE_VERIFICATION_FAILED");
  }
  return data as ChallengeConsumeResponse;
}

export async function registerCandidateUser(
  payload: RegisterUserPayload
): Promise<RegisterUserResponse> {
  const res = await fetch("/api/bff/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || data.error || "REGISTRATION_FAILED");
  }
  return data as RegisterUserResponse;
}













