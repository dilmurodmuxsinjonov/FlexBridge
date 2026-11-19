import { errorText } from "@/lib/errorText";

export interface PasskeyOverviewItem {
  id: string;
  device_type?: string | null;
  backed_up?: boolean;
  created_at?: string | null;
  last_used_at?: string | null;
}

export interface UserContactItem {
  id: string;
  channel: "PHONE" | "EMAIL" | string;
  masked_destination: string;
  is_primary: boolean;
  verified_at?: string | null;
}

export interface ChallengeResendResponse {
  ok: boolean;
  challenge_id: string;
  delivery_method?: "SMS" | "TELEGRAM" | "EMAIL";
  telegram_bot_username?: string;
  telegram_deep_link?: string;
  expires_in?: number;
  resend_after?: number;
}

export interface PasskeyCeremonyOptions {
  ceremony_token: string;
  public_key: Record<string, unknown>;
  expires_in: number;
}

async function callJson<T>(url: string, init: RequestInit, fallbackError: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store", ...init });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.ok === false) {
    const rawCode =
      typeof data?.error === "string"
        ? data.error
        : typeof data?.detail?.code === "string"
        ? data.detail.code
        : undefined;
    const err = new Error(errorText(data, fallbackError));
    (err as unknown as { status: number; code?: string }).status = res.status;
    (err as unknown as { status: number; code?: string }).code = rawCode || fallbackError;
    throw err;
  }
  return data as T;
}

const jsonInit = (method: "POST" | "PATCH" | "DELETE", body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: JSON.stringify(body),
});

export function resendAuthChallenge(
  challengeId: string,
  purpose: "REGISTER" | "LOGIN" | "RECOVERY" | "CONTACT"
) {
  return callJson<ChallengeResendResponse>(
    `/api/bff/auth/challenges/${encodeURIComponent(challengeId)}/resend`,
    jsonInit("POST", { purpose }),
    "CHALLENGE_RESEND_FAILED"
  );
}

export async function issueOrResendRegisterChallenge(params: {
  challengeId: string | null;
  sentKey: string | null;
  channel: "PHONE" | "EMAIL";
  destination: string;
  deliveryMethod: "SMS" | "TELEGRAM";
  issueFn: () => Promise<ChallengeResendResponse>;
}): Promise<{ res: ChallengeResendResponse; nextKey: string; resent: boolean }> {
  const nextKey = `${params.channel}:${params.destination}:${params.deliveryMethod}`;
  if (params.challengeId && params.sentKey === nextKey) {
    const res = await resendAuthChallenge(params.challengeId, "REGISTER");
    return { res, nextKey, resent: true };
  }
  const res = await params.issueFn();
  return { res, nextKey, resent: false };
}

export async function fetchMyContacts(): Promise<UserContactItem[]> {
  const res = await callJson<{ items?: UserContactItem[] }>(
    "/api/bff/me/contacts",
    { method: "GET", headers: { Accept: "application/json" } },
    "CONTACTS_FETCH_FAILED"
  );
  return res.items || [];
}

export function startContactChallenge(
  channel: "PHONE" | "EMAIL",
  destination: string,
  deliveryMethod: "SMS" | "TELEGRAM" | "EMAIL"
) {
  return callJson<ChallengeResendResponse>(
    "/api/bff/auth/challenges",
    jsonInit("POST", { channel, destination, purpose: "CONTACT", delivery_method: deliveryMethod }),
    "CHALLENGE_FAILED"
  );
}

export function consumeContactChallenge(challengeId: string, code: string) {
  return callJson<{ verification_token: string }>(
    `/api/bff/auth/challenges/${encodeURIComponent(challengeId)}/consume`,
    jsonInit("POST", { purpose: "CONTACT", code }),
    "CODE_VERIFICATION_FAILED"
  );
}

export function bindSecondaryContact(payload: {
  verification_token: string;
  current_password: string;
  totp_code?: string;
}) {
  return callJson<{ contact_id: string; verified: boolean }>(
    "/api/bff/me/contacts",
    jsonInit("POST", payload),
    "CONTACT_BIND_FAILED"
  );
}

export function startPasskeyRegistration(currentPassword: string, totpCode?: string) {
  return callJson<PasskeyCeremonyOptions>(
    "/api/bff/me/security/passkeys/options",
    jsonInit("POST", {
      current_password: currentPassword,
      ...(totpCode ? { totp_code: totpCode } : {}),
    }),
    "PASSKEY_OPTIONS_FAILED"
  );
}

export function finishPasskeyRegistration(ceremonyToken: string, credential: Record<string, unknown>) {
  return callJson<{ credential_id: string; passkey_enabled: boolean; reauthentication_required?: boolean }>(
    "/api/bff/me/security/passkeys/verify",
    jsonInit("POST", { ceremony_token: ceremonyToken, credential }),
    "PASSKEY_REGISTER_FAILED"
  );
}

export function revokePasskey(credentialId: string, currentPassword: string, totpCode?: string) {
  return callJson<{ status: string; reauthentication_required?: boolean }>(
    `/api/bff/me/security/passkeys/${encodeURIComponent(credentialId)}`,
    jsonInit("DELETE", {
      current_password: currentPassword,
      ...(totpCode ? { totp_code: totpCode } : {}),
    }),
    "PASSKEY_REVOKE_FAILED"
  );
}

export function startPasskeyLogin(mfaTicket?: string) {
  return callJson<PasskeyCeremonyOptions>(
    "/api/auth/passkeys/options",
    jsonInit("POST", mfaTicket ? { mfa_ticket: mfaTicket } : {}),
    "PASSKEY_OPTIONS_FAILED"
  );
}

export function finishPasskeyLogin(
  ceremonyToken: string,
  credential: Record<string, unknown>,
  portal?: string
) {
  return callJson<{ ok: boolean; user_id: string; roles: string[] }>(
    "/api/auth/passkeys/verify",
    jsonInit("POST", {
      ceremony_token: ceremonyToken,
      credential,
      ...(portal ? { portal } : {}),
    }),
    "PASSKEY_VERIFICATION_FAILED"
  );
}

export function updateMyProfile(displayName: string) {
  return callJson<{ user_id: string; display_name: string }>(
    "/api/bff/me/profile",
    jsonInit("PATCH", { display_name: displayName }),
    "PROFILE_UPDATE_FAILED"
  );
}

export function changeMyPassword(currentPassword: string, newPassword: string, totpCode?: string) {
  return callJson<{ password_updated: boolean; revoked_other_sessions: number; reauthentication_required?: boolean }>(
    "/api/bff/me/security/password",
    jsonInit("POST", {
      current_password: currentPassword,
      new_password: newPassword,
      ...(totpCode ? { totp_code: totpCode } : {}),
    }),
    "PASSWORD_CHANGE_FAILED"
  );
}

export function setPrimaryContact(contactId: string, currentPassword: string, totpCode?: string) {
  return callJson<{ contact_id: string; channel: "EMAIL" | "PHONE"; is_primary: boolean }>(
    `/api/bff/me/contacts/${encodeURIComponent(contactId)}/primary`,
    jsonInit("PATCH", {
      current_password: currentPassword,
      ...(totpCode ? { totp_code: totpCode } : {}),
    }),
    "CONTACT_PRIMARY_UPDATE_FAILED"
  );
}

export function removeMyContact(contactId: string, currentPassword: string, totpCode?: string) {
  return callJson<{ contact_id: string; removed: boolean; promoted_primary_contact_id?: string | null }>(
    `/api/bff/me/contacts/${encodeURIComponent(contactId)}`,
    jsonInit("DELETE", {
      current_password: currentPassword,
      ...(totpCode ? { totp_code: totpCode } : {}),
    }),
    "CONTACT_REMOVE_FAILED"
  );
}
