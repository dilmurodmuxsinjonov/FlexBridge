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
