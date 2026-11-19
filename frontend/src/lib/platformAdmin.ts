import { errorText } from "@/lib/errorText";

export interface RoleCatalogItem {
  code: string;
  scope_kind?: string;
  description?: string | null;
}

export interface StaffGrantItem {
  id: string;
  grant_id?: string;
  user_id: string;
  display_name?: string | null;
  user_display_name?: string | null;
  masked_contact?: string | null;
  role_code: string;
  granter_id?: string | null;
  granted_by_id?: string | null;
  granter_display_name?: string | null;
  granted_by_display_name?: string | null;
  reason?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
  is_permanent?: boolean;
}

export interface StaffGrantsResponse {
  ok: boolean;
  contract_id?: string;
  roles_catalog?: RoleCatalogItem[] | string[];
  active_grants: StaffGrantItem[];
  recent_revoked: StaffGrantItem[];
  role_matrix?: Array<Record<string, unknown>>;
}

export interface GrantStaffRolePayload {
  user_id: string;
  role_code: string;
  reason: string;
  duration_days?: number;
}

export interface GrantStaffRoleResult {
  ok: boolean;
  grant_id: string;
  user_id: string;
  role_code: string;
  expires_at: string;
}

export interface DirectoryUserItem {
  id: string;
  display_name: string | null;
  status: string;
  masked_contact?: string | null;
  mfa_enabled: boolean;
  platform_roles: string[];
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface DirectoryOrganizationItem {
  id: string;
  public_name: string | null;
  legal_name: string | null;
  tax_id?: string | null;
  region?: string | null;
  verification_status: string;
  active_members_count?: number;
  published_opportunities_count?: number;
  created_at?: string | null;
}

export interface DirectoryInstitutionItem {
  id: string;
  official_name: string | null;
  short_name?: string | null;
  registry_code?: string | null;
  tax_id?: string | null;
  region?: string | null;
  verification_status: string;
  verified_students_count?: number;
  active_staff_count?: number;
  created_at?: string | null;
}

export interface FeatureFlagItem {
  code: string;
  category: "R1" | "PROTECTED" | "R2";
  enabled: boolean;
  version: number;
  mutable: boolean;
  disable_only: boolean;
  updated_at?: string | null;
  reason?: string | null;
  alias_of?: string | null;
}

export interface PatchFeatureFlagResult {
  ok: boolean;
  code: string;
  enabled: boolean;
  effective_enabled?: boolean;
  version: number;
  reason?: string | null;
  decided_at?: string | null;
}

export interface PrivacyRequestItem {
  id: string;
  user_id: string;
  display_name?: string | null;
  kind: string;
  status: string;
  reason?: string | null;
  due_at?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface RecoveryMaskedContact {
  channel: string;
  masked: string;
}

export interface RecoveryRequestItem {
  id: string;
  user_id: string;
  display_name?: string | null;
  status: string;
  masked_contacts?: RecoveryMaskedContact[];
  created_at?: string | null;
  resolved_at?: string | null;
  reviewer_id?: string | null;
}

export interface ModerationAppealItem {
  case_id: string;
  created_at?: string | null;
  status: string;
  due_at?: string | null;
}

export interface OwnerContinuityCaseItem {
  id: string;
  organization_id: string;
  status: string;
  due_at?: string | null;
  created_at?: string | null;
}

export interface PilotReadinessReport {
  pilot_ready: boolean;
  acceptance_status: string;
  schema_migrated: boolean;
  finance_circuit_state: string;
  release_stage: string;
  r2_freelance_enabled: boolean;
  feature_flag_read_status: string;
  disaster_recovery_targets?: {
    rpo_hours: number;
    rto_hours: number;
    restore_drill_verified: boolean;
  };
  infrastructure?: {
    status?: string;
    checks?: Record<string, boolean>;
  };
}

export interface RetentionEvaluationResult {
  id: string;
  data_category: string;
  age_days: number;
  mode: string;
  status: string;
  records_scanned: number;
  records_actioned: number;
  idempotent_replay?: boolean;
  evaluation?: {
    outcome?: string;
    active_days?: number;
    backup_expiry_days?: number;
  };
}

export const RETENTION_CATEGORIES = [
  "OTP_CHALLENGE_DIGEST",
  "SECURITY_LOGIN_METADATA",
  "PRIVATE_EXPORT_FILE",
  "UNPUBLISHED_DRAFT",
  "VERIFICATION_EVIDENCE",
  "APPLICATION_AND_SNAPSHOT",
  "INTERNSHIP_DIARY_ACADEMIC",
  "BILLING_AND_FISCAL_LEDGER",
] as const;

export function makeIdempotencyKey(prefix: string): string {
  const random =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  return `${prefix}-${random}`.slice(0, 120);
}

async function bffCall<T>(
  url: string,
  init: RequestInit | undefined,
  fallbackError: string
): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(errorText(data, fallbackError));
  }
  return data as T;
}

export function fetchStaffGrants(): Promise<StaffGrantsResponse> {
  return bffCall<StaffGrantsResponse>("/api/bff/operator/staff-grants", undefined, "STAFF_GRANTS_FETCH_FAILED");
}

export function grantStaffRole(payload: GrantStaffRolePayload): Promise<GrantStaffRoleResult> {
  return bffCall<GrantStaffRoleResult>(
    "/api/bff/operator/staff-grants",
    { method: "POST", body: JSON.stringify(payload) },
    "STAFF_GRANT_FAILED"
  );
}

export function revokeStaffRole(grantId: string, reason: string): Promise<{ ok: boolean }> {
  return bffCall<{ ok: boolean }>(
    `/api/bff/operator/staff-grants/${encodeURIComponent(grantId)}/revoke`,
    { method: "POST", body: JSON.stringify({ reason }) },
    "STAFF_REVOKE_FAILED"
  );
}

export function fetchDirectoryUsers(params?: { q?: string; role?: string; limit?: number }): Promise<DirectoryUserItem[]> {
  const qs = new URLSearchParams();
  if (params?.q?.trim()) qs.set("q", params.q.trim());
  if (params?.role?.trim()) qs.set("role", params.role.trim());
  qs.set("limit", String(params?.limit ?? 40));
  return bffCall<{ items?: DirectoryUserItem[] }>(
    `/api/bff/operator/directory/users?${qs.toString()}`,
    undefined,
    "DIRECTORY_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function fetchDirectoryOrganizations(params?: { q?: string; status?: string; limit?: number }): Promise<DirectoryOrganizationItem[]> {
  const qs = new URLSearchParams();
  if (params?.q?.trim()) qs.set("q", params.q.trim());
  if (params?.status?.trim()) qs.set("status", params.status.trim());
  qs.set("limit", String(params?.limit ?? 40));
  return bffCall<{ items?: DirectoryOrganizationItem[] }>(
    `/api/bff/operator/directory/organizations?${qs.toString()}`,
    undefined,
    "DIRECTORY_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function fetchDirectoryInstitutions(params?: { q?: string; status?: string; limit?: number }): Promise<DirectoryInstitutionItem[]> {
  const qs = new URLSearchParams();
  if (params?.q?.trim()) qs.set("q", params.q.trim());
  if (params?.status?.trim()) qs.set("status", params.status.trim());
  qs.set("limit", String(params?.limit ?? 40));
  return bffCall<{ items?: DirectoryInstitutionItem[] }>(
    `/api/bff/operator/directory/institutions?${qs.toString()}`,
    undefined,
    "DIRECTORY_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function fetchFeatureFlags(): Promise<FeatureFlagItem[]> {
  return bffCall<{ items?: FeatureFlagItem[] }>(
    "/api/bff/operator/feature-flags",
    undefined,
    "FEATURE_FLAGS_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function patchFeatureFlag(
  code: string,
  payload: { enabled: boolean; reason: string; expectedVersion: number }
): Promise<PatchFeatureFlagResult> {
  return bffCall<PatchFeatureFlagResult>(
    `/api/bff/operator/feature-flags/${encodeURIComponent(code)}`,
    {
      method: "PATCH",
      headers: {
        "Idempotency-Key": makeIdempotencyKey("ff-toggle"),
        "If-Match": `"${payload.expectedVersion}"`,
      },
      body: JSON.stringify({ enabled: payload.enabled, reason: payload.reason }),
    },
    "FEATURE_FLAG_UPDATE_FAILED"
  );
}

export function fetchPrivacyRequests(params?: { status?: string; limit?: number }): Promise<PrivacyRequestItem[]> {
  const qs = new URLSearchParams();
  if (params?.status?.trim()) qs.set("status", params.status.trim());
  qs.set("limit", String(params?.limit ?? 50));
  return bffCall<{ items?: PrivacyRequestItem[] }>(
    `/api/bff/operator/privacy-requests?${qs.toString()}`,
    undefined,
    "PRIVACY_REQUESTS_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function resolvePrivacyRequest(
  id: string,
  payload: { status: "RESOLVED" | "REJECTED"; reason: string }
): Promise<{ ok: boolean }> {
  return bffCall<{ ok: boolean }>(
    `/api/bff/operator/privacy-requests/${encodeURIComponent(id)}/resolve`,
    { method: "POST", body: JSON.stringify(payload) },
    "RESOLVE_PRIVACY_REQUEST_FAILED"
  );
}

export function fetchRecoveryRequests(params?: { status?: string; limit?: number }): Promise<RecoveryRequestItem[]> {
  const qs = new URLSearchParams();
  qs.set("status", params?.status?.trim() || "PENDING_REVIEW");
  qs.set("limit", String(params?.limit ?? 50));
  return bffCall<{ items?: RecoveryRequestItem[] }>(
    `/api/bff/operator/recovery-requests?${qs.toString()}`,
    undefined,
    "RECOVERY_REQUESTS_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function decideRecoveryRequest(
  id: string,
  payload: { decision: "APPROVE" | "REJECT"; reason: string }
): Promise<{ ok: boolean; id: string; status: string; valid_until?: string | null }> {
  return bffCall<{ ok: boolean; id: string; status: string; valid_until?: string | null }>(
    `/api/bff/operator/recovery-requests/${encodeURIComponent(id)}/decide`,
    { method: "POST", body: JSON.stringify(payload) },
    "RECOVERY_DECISION_FAILED"
  );
}

export function fetchModerationAppeals(limit = 50): Promise<ModerationAppealItem[]> {
  return bffCall<{ items?: ModerationAppealItem[] }>(
    `/api/bff/operator/moderation-appeals?limit=${limit}`,
    undefined,
    "MODERATION_APPEALS_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function claimModerationAppeal(caseId: string): Promise<{ ok: boolean; status?: string }> {
  return bffCall<{ ok: boolean; status?: string }>(
    `/api/bff/operator/moderation-appeals/${encodeURIComponent(caseId)}/claim`,
    { method: "POST", body: JSON.stringify({}) },
    "APPEAL_CLAIM_FAILED"
  );
}

export function decideModerationAppeal(
  caseId: string,
  payload: { decision: "UPHOLD" | "REOPEN"; reason: string }
): Promise<{ ok: boolean; status?: string; decision?: string }> {
  return bffCall<{ ok: boolean; status?: string; decision?: string }>(
    `/api/bff/operator/moderation-appeals/${encodeURIComponent(caseId)}/decide`,
    { method: "POST", body: JSON.stringify(payload) },
    "APPEAL_DECIDE_FAILED"
  );
}

export function fetchOwnerContinuityCases(
  stage: "MODERATOR" | "COMPLIANCE",
  params?: { unassigned?: boolean; limit?: number }
): Promise<OwnerContinuityCaseItem[]> {
  const qs = new URLSearchParams();
  if (params?.unassigned !== undefined) qs.set("unassigned", String(params.unassigned));
  qs.set("limit", String(params?.limit ?? 50));
  return bffCall<{ items?: OwnerContinuityCaseItem[] }>(
    `/api/bff/operator/owner-continuity/${stage}?${qs.toString()}`,
    undefined,
    "OWNER_CONTINUITY_FETCH_FAILED"
  ).then((d) => d.items ?? []);
}

export function claimOwnerContinuityCase(
  stage: "MODERATOR" | "COMPLIANCE",
  caseId: string
): Promise<{ ok: boolean }> {
  return bffCall<{ ok: boolean }>(
    `/api/bff/operator/owner-continuity/${stage}/${encodeURIComponent(caseId)}/claim`,
    { method: "POST", body: JSON.stringify({}) },
    "CONTINUITY_CLAIM_FAILED"
  );
}

export function decideOwnerContinuityCase(
  stage: "MODERATOR" | "COMPLIANCE",
  caseId: string,
  payload: { decision: "RECOMMEND" | "APPROVE" | "REJECT" | "NEEDS_INFO"; reason: string; expected_revision?: number }
): Promise<{ ok: boolean }> {
  return bffCall<{ ok: boolean }>(
    `/api/bff/operator/owner-continuity/${stage}/${encodeURIComponent(caseId)}/decide`,
    {
      method: "POST",
      body: JSON.stringify({
        decision: payload.decision,
        expected_revision: payload.expected_revision ?? 1,
        reason: payload.reason,
      }),
    },
    "CONTINUITY_DECIDE_FAILED"
  );
}

export function fetchPilotReadiness(): Promise<PilotReadinessReport> {
  return bffCall<PilotReadinessReport>(
    "/api/bff/operator/operations/pilot-readiness",
    undefined,
    "PILOT_READINESS_FETCH_FAILED"
  );
}

export function evaluateRetentionDryRun(payload: {
  data_category: string;
  age_days: number;
}): Promise<RetentionEvaluationResult> {
  return bffCall<RetentionEvaluationResult>(
    "/api/bff/operator/operations/retention-executions",
    {
      method: "POST",
      headers: { "Idempotency-Key": makeIdempotencyKey("retention") },
      body: JSON.stringify({
        data_category: payload.data_category,
        age_days: payload.age_days,
        records_scanned: 0,
      }),
    },
    "RETENTION_EVALUATION_FAILED"
  );
}
