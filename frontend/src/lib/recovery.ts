/**
 * Client calls for self-service password recovery (backend IAM.md "Contact va recovery"):
 * RECOVERY OTP -> proof -> (TOTP | backup code) -> reset token -> new password.
 * Errors are thrown as RecoveryError carrying the backend machine code.
 */
export class RecoveryError extends Error {
  constructor(public code: string, public status: number) {
    super(code);
  }
}

async function call<T>(url: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { ...init, cache: "no-store" });
  } catch {
    throw new RecoveryError("INTERNAL_ERROR", 0);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const code =
      res.status === 429
        ? "RATE_LIMITED"
        : (data?.detail && typeof data.detail === "object" && data.detail.code) || data?.error || "RECOVERY_FAILED";
    throw new RecoveryError(String(code), res.status);
  }
  return data as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: JSON.stringify(body),
});

export type RecoveryChannel = "PHONE" | "EMAIL";
export type RecoveryDelivery = "SMS" | "TELEGRAM" | "EMAIL";

export interface RecoveryChallenge {
  challenge_id: string;
  delivery_method?: RecoveryDelivery;
  telegram_bot_username?: string;
  telegram_deep_link?: string;
  expires_in: number;
  resend_after: number;
}

export interface RecoveryRequestResult {
  recovery_id: string;
  recovery_token: string;
  status: "READY_TO_RESET" | "PENDING_REVIEW" | string;
  reset_token?: string;
  expires_in: number;
}

/** "+998 90 123-45-67" -> "+998901234567"; a bare 9-digit Uzbek number gets +998. */
export function normalizeRecoveryDestination(raw: string): { channel: RecoveryChannel; destination: string } {
  const value = raw.trim();
  if (value.includes("@")) return { channel: "EMAIL", destination: value };
  let digits = value.replace(/[\s()-]/g, "");
  if (/^[0-9]{9}$/.test(digits)) digits = "+998" + digits;
  else if (/^998[0-9]{9}$/.test(digits)) digits = "+" + digits;
  return { channel: "PHONE", destination: digits };
}

export function startRecovery(channel: RecoveryChannel, destination: string, delivery: RecoveryDelivery) {
  return call<RecoveryChallenge>("/api/bff/auth/challenges", json({ channel, destination, purpose: "RECOVERY", delivery_method: delivery }));
}

export function verifyRecoveryCode(challengeId: string, code: string) {
  return call<{ verification_token: string }>(
    `/api/bff/auth/challenges/${encodeURIComponent(challengeId)}/consume`,
    json({ purpose: "RECOVERY", code })
  );
}

export function requestRecovery(verificationToken: string, factor: { totp_code?: string; recovery_code?: string }) {
  return call<RecoveryRequestResult>("/api/bff/auth/recovery", json({ verification_token: verificationToken, ...factor }));
}

export function fetchRecoveryStatus(recoveryId: string, recoveryToken: string) {
  return call<{ recovery_id: string; status: string }>(`/api/bff/auth/recovery/${encodeURIComponent(recoveryId)}`, {
    method: "GET",
    headers: { Accept: "application/json", "X-Recovery-Token": recoveryToken },
  });
}

export function completeRecovery(recoveryId: string, resetToken: string, newPassword: string) {
  return call<{ status: string; reauthentication_required: boolean }>(
    `/api/bff/auth/recovery/${encodeURIComponent(recoveryId)}/complete`,
    json({ reset_token: resetToken, new_password: newPassword })
  );
}
