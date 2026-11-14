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
