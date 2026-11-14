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
