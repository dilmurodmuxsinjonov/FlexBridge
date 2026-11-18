import { errorText } from "@/lib/errorText";

export interface PublicServiceItem {
  code: string;
  name_uz: string;
  target_audience: string;
  is_active: boolean;
  stage: number;
  description: string;
  conditions: string[];
}

export interface PublicServicesResponse {
  contract_id: string;
  currency: string;
  updated_at: string;
  services: PublicServiceItem[];
}

export interface PublicPricePlan {
  tier: string;
  title: string;
  plan_code: string;
  price_uzs: number;
  duration_days: number;
  description: string;
  opportunity_slots: number;
}

export interface PublicPricesResponse {
  contract_id: string;
  currency: string;
  pricing_model: string;
  plans: PublicPricePlan[];
  activation_rules: {
    speed: string;
    provider: string;
    currency: string;
  };
  refund_policy: {
    policy: string;
    full_refund_window_hours: number;
    description: string;
    circuit_breaker_guarantee: boolean;
  };
}

export interface PublicOrganizationProfile {
  contract_id: string;
  id: string;
  public_name: string;
  region: string | null;
  description: string | null;
  website: string | null;
  capabilities: string[];
}

export interface PublicOrganizationOpportunity {
  id: string;
  title: string;
  kind: string;
  work_mode: string;
  location: string;
  capacity: number;
  occupied_count: number;
  vacancies_available: number;
  status: string;
  created_at: string;
}

export interface PublicOrganizationOpportunitiesResponse {
  contract_id: string;
  organization_id: string;
  items: PublicOrganizationOpportunity[];
  limit: number;
  has_more: boolean;
  next_cursor: string | null;
}

export interface PublicOrganizationRatingSummary {
  contract_id: string;
  target_org_id: string;
  score: number | null;
  score_status: "UNRATED" | "WITHHELD_INSUFFICIENT_SAMPLE" | "PUBLISHED" | string;
  sample_size: number;
  feature_flag: string;
  feature_enabled: boolean;
  computed_at: string | null;
}

export interface CreateModerationCaseInput {
  category: string;
  reason: string;
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  opportunity_id?: string;
  organization_id?: string;
}

export interface CreateModerationCaseResult {
  id: string;
  status: string;
  severity: string;
  category: string;
  due_at?: string;
}

async function fetchJson<T>(url: string, fallbackError: string): Promise<T> {
  const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const err = new Error(errorText(data, fallbackError));
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as T;
}

export function fetchPublicServices(): Promise<PublicServicesResponse> {
  return fetchJson<PublicServicesResponse>("/api/bff/public/services", "SERVICES_UNAVAILABLE");
}

export function fetchPublicPrices(): Promise<PublicPricesResponse> {
  return fetchJson<PublicPricesResponse>("/api/bff/public/prices", "PRICES_UNAVAILABLE");
}

export function fetchPublicOrganization(id: string): Promise<PublicOrganizationProfile> {
  return fetchJson<PublicOrganizationProfile>(
    `/api/bff/organizations/${encodeURIComponent(id)}/public`,
    "ORGANIZATION_NOT_FOUND"
  );
}

export function fetchPublicOrganizationOpportunities(
  id: string,
  params?: { limit?: number; after?: string | null }
): Promise<PublicOrganizationOpportunitiesResponse> {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.after) sp.set("after", params.after);
  const qs = sp.toString();
  return fetchJson<PublicOrganizationOpportunitiesResponse>(
    `/api/bff/organizations/${encodeURIComponent(id)}/opportunities${qs ? `?${qs}` : ""}`,
    "ORGANIZATION_OPPORTUNITIES_FAILED"
  );
}

export function fetchPublicOrganizationRatingSummary(
  id: string
): Promise<PublicOrganizationRatingSummary> {
  return fetchJson<PublicOrganizationRatingSummary>(
    `/api/bff/organizations/${encodeURIComponent(id)}/rating-summary`,
    "RATING_SUMMARY_FAILED"
  );
}

export async function submitModerationCase(
  payload: CreateModerationCaseInput
): Promise<CreateModerationCaseResult> {
  const res = await fetch("/api/bff/moderation-cases", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const err = new Error(errorText(data, "MODERATION_REPORT_FAILED"));
    (err as unknown as { status: number }).status = res.status;
    throw err;
  }
  return data as CreateModerationCaseResult;
}

/** Ensures external organization URLs strictly use http(s) before rendering as href. */
export function safeExternalWebsiteUrl(raw: string | null | undefined): string | null {
  if (!raw || typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  try {
    const candidate = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    const url = new URL(candidate);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return url.toString();
  } catch {
    return null;
  }
}
