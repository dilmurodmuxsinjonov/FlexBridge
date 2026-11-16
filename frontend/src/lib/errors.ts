export const SIGN_IN_REQUIRED_MESSAGE = "Tizimga kirish talab etiladi. Iltimos, profilingizga kiring.";

/**
 * User-facing message for a failed BFF request. `lib/api.ts` attaches the HTTP
 * status to thrown errors; 401 always means the session is missing or expired.
 */
export function describeRequestError(err: unknown, fallback: string): string {
  if (err && typeof err === "object" && (err as { status?: unknown }).status === 401) {
    return SIGN_IN_REQUIRED_MESSAGE;
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

const LOGIN_ERROR_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "Telefon/pochta yoki parol noto‘g‘ri. Qaytadan tekshirib ko‘ring.",
  LOGIN_FAILED: "Kirib bo‘lmadi. Telefon/pochta va parolni tekshiring.",
  RATE_LIMITED: "Juda ko‘p urinish bo‘ldi. Bir necha daqiqadan so‘ng qayta urinib ko‘ring.",
  TOTP_REQUIRED_OR_INVALID: "Kod noto‘g‘ri yoki muddati o‘tgan. Ilovadagi yangi kodni kiriting.",
  MFA_VERIFICATION_FAILED: "Kod noto‘g‘ri yoki muddati o‘tgan. Ilovadagi yangi kodni kiriting.",
  MFA_REQUIRED: "Bu hisob uchun qo‘shimcha tasdiqlash talab qilinadi.",
  MFA_ENROLLMENT_REQUIRED: "Bu hisob uchun avval ikki bosqichli himoyani yoqish kerak. Administratorga murojaat qiling.",
  AUTH_REVOKED: "Sessiya bekor qilingan. Qaytadan kiring.",
  SESSION_EXPIRED: "Sessiya muddati tugagan. Qaytadan kiring.",
  CSRF_ORIGIN_MISMATCH: "So‘rov boshqa manzildan yuborildi. Sahifani yangilab, qayta urinib ko‘ring.",
  EMAIL_OR_DESTINATION_AND_PASSWORD_REQUIRED: "Telefon/pochta va parolni kiriting.",
  MFA_TICKET_AND_CODE_REQUIRED: "6 xonali kodni kiriting.",
  INTERNAL_ERROR: "Server bilan bog‘lanib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.",
};

/**
 * Turns a sign-in error (backend/BFF code such as `INVALID_CREDENTIALS`, or an
 * already human-readable sentence) into a short Uzbek message.
 */
export function describeLoginError(error: string | null | undefined): string {
  const raw = (error || "").trim();
  if (!raw) return LOGIN_ERROR_MESSAGES.LOGIN_FAILED;
  if (LOGIN_ERROR_MESSAGES[raw]) return LOGIN_ERROR_MESSAGES[raw];
  // Unknown machine code (UPPER_SNAKE) — never show it raw.
  if (/^[A-Z0-9_]+$/.test(raw)) return LOGIN_ERROR_MESSAGES.LOGIN_FAILED;
  if (/failed to fetch|networkerror|load failed/i.test(raw)) return LOGIN_ERROR_MESSAGES.INTERNAL_ERROR;
  return raw;
}
