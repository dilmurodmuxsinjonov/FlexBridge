import { cookies } from "next/headers";
import crypto from "crypto";

export interface SessionData {
  token: string;
  access_token?: string;
  user_id: string;
  roles: string[];
  expires_at: number;
}

const COOKIE_NAME = "flexbridge_session";

// Server-side encryption key derived deterministically via SHA-256
function getEncryptionKey(): Buffer {
  const secret = process.env.BFF_SESSION_SECRET || "flexbridge-staging-bff-session-secret-at-least-32-chars-long-2026";
  return crypto.createHash("sha256").update(secret).digest();
}

/**
 * Encrypts a session payload using AES-256-GCM with authenticated authentication tag.
 * Output format: base64url(iv):base64url(tag):base64url(ciphertext)
 */
export function encryptSession(data: SessionData): string {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  
  const plaintext = JSON.stringify(data);
  const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();

  return `${iv.toString("base64url")}.${tag.toString("base64url")}.${encrypted.toString("base64url")}`;
}

/**
 * Decrypts and verifies an AES-256-GCM encrypted session string.
 * Returns null if the format is invalid, tampering is detected, or the session has expired.
 */
export function decryptSession(encryptedText: string): SessionData | null {
  try {
    const parts = encryptedText.split(".");
    if (parts.length !== 3) return null;

    const [ivB64, tagB64, dataB64] = parts;
    const iv = Buffer.from(ivB64, "base64url");
    const tag = Buffer.from(tagB64, "base64url");
    const encrypted = Buffer.from(dataB64, "base64url");

    if (iv.length !== 12 || tag.length !== 16) return null;

    const key = getEncryptionKey();
    const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
    decipher.setAuthTag(tag);

    const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
    const parsed = JSON.parse(decrypted.toString("utf8")) as SessionData;

    if (!parsed || typeof parsed.token !== "string" || typeof parsed.user_id !== "string") {
      return null;
    }

    if (parsed.expires_at && parsed.expires_at < Math.floor(Date.now() / 1000)) {
      return null; // Expired
    }

    return parsed;
  } catch {
    return null; // Decryption failure, tampered tag, or corrupted JSON
  }
}

/**
 * Retrieves the currently active session from the server-side HttpOnly cookie.
 */
export async function getSession(): Promise<SessionData | null> {
  const cookieStore = await cookies();
  const cookie = cookieStore.get(COOKIE_NAME);
  if (!cookie?.value) return null;
  return decryptSession(cookie.value);
}

/**
 * Retrieves session from cookie and provides access_token alias for token.
 */
export async function getSessionFromCookie(): Promise<(SessionData & { access_token: string }) | null> {
  const session = await getSession();
  if (!session) return null;
  return {
    ...session,
    access_token: session.token,
  };
}

/**
 * Sets the encrypted session HttpOnly cookie on the response.
 */
export async function setSessionCookie(data: SessionData): Promise<void> {
  const cookieStore = await cookies();
  const encrypted = encryptSession(data);
  const maxAge = Math.max(60, data.expires_at - Math.floor(Date.now() / 1000));

  cookieStore.set(COOKIE_NAME, encrypted, {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE === "true",
    sameSite: "lax",
    path: "/",
    maxAge: maxAge,
  });
}

/**
 * Clears the session HttpOnly cookie.
 */
export async function clearSessionCookie(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

/**
 * Low-level backend fetch helper running purely on the server.
 * Never exposes backend tokens or internal infrastructure to the browser.
 */
export async function backendFetch(
  path: string,
  init?: RequestInit,
  sessionToken?: string
): Promise<Response> {
  const baseUrl = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const url = `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  const headers = new Headers(init?.headers || {});
  headers.set("Accept", "application/json");
  if (sessionToken) {
    headers.set("Authorization", `Bearer ${sessionToken}`);
  }

  return fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });
}

/**
 * Checks request origin against host to prevent CSRF on mutating BFF routes.
 */
export function verifyCsrfOrigin(request: Request): boolean {
  if (["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    return true;
  }

  const origin = request.headers.get("origin");
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host");

  if (!origin || !host) {
    // If no origin is provided (e.g. native client or curl in test), allow only if Sec-Fetch-Site is not cross-site
    const secFetchSite = request.headers.get("sec-fetch-site");
    if (secFetchSite === "cross-site") return false;
    return true;
  }

  try {
    const originHost = new URL(origin).host;
    return originHost === host;
  } catch {
    return false;
  }
}
