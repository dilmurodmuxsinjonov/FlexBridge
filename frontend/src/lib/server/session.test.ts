// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from "vitest";
import { decryptSession, encryptSession, getEncryptionKey, verifyCsrfOrigin, type SessionData } from "./session";

const LONG_SECRET = "unit-test-bff-session-secret-0123456789abcdef";

function session(overrides: Partial<SessionData> = {}): SessionData {
  return {
    token: "backend-token",
    user_id: "user-1",
    roles: ["CANDIDATE"],
    expires_at: Math.floor(Date.now() / 1000) + 600,
    ...overrides,
  };
}

function resetEphemeralKey() {
  delete (globalThis as { __flexbridgeEphemeralSessionKey?: Buffer }).__flexbridgeEphemeralSessionKey;
}

describe("session encryption", () => {
  beforeEach(() => {
    vi.stubEnv("BFF_SESSION_SECRET", LONG_SECRET);
  });

  it("round-trips a session", () => {
    const data = session({ roles: ["CANDIDATE", "HR"] });
    expect(decryptSession(encryptSession(data))).toEqual(data);
  });

  it("uses a fresh IV so equal payloads encrypt differently", () => {
    const data = session();
    expect(encryptSession(data)).not.toEqual(encryptSession(data));
  });

  it("rejects a tampered ciphertext", () => {
    const [iv, tag, body] = encryptSession(session()).split(".");
    const flipped = Buffer.from(body, "base64url");
    flipped[0] ^= 0xff;
    expect(decryptSession(`${iv}.${tag}.${flipped.toString("base64url")}`)).toBeNull();
  });

  it("rejects malformed input", () => {
    expect(decryptSession("not-a-session")).toBeNull();
    expect(decryptSession("a.b.c")).toBeNull();
  });

  it("rejects an expired session", () => {
    expect(decryptSession(encryptSession(session({ expires_at: 1 })))).toBeNull();
  });

  it("rejects a cookie minted with a different secret", () => {
    const cookie = encryptSession(session());
    vi.stubEnv("BFF_SESSION_SECRET", `${LONG_SECRET}-rotated`);
    expect(decryptSession(cookie)).toBeNull();
  });
});

describe("getEncryptionKey", () => {
  beforeEach(() => {
    resetEphemeralKey();
  });

  it("rejects a configured secret shorter than 32 characters", () => {
    expect(() => getEncryptionKey({ BFF_SESSION_SECRET: "short", NODE_ENV: "production" })).toThrow(/32/);
  });

  it("never falls back to a repository constant in production", () => {
    const devKey = getEncryptionKey({ NODE_ENV: "development" });
    const prodKey = getEncryptionKey({ NODE_ENV: "production" });
    expect(prodKey.equals(devKey)).toBe(false);
    expect(prodKey).toHaveLength(32);
  });

  it("keeps the production ephemeral key stable within the process", () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const first = getEncryptionKey({ NODE_ENV: "production" });
    const second = getEncryptionKey({ NODE_ENV: "production" });
    expect(second.equals(first)).toBe(true);
    expect(console.warn).toHaveBeenCalledTimes(1);
  });

  it("derives the same key from the same configured secret", () => {
    const a = getEncryptionKey({ BFF_SESSION_SECRET: LONG_SECRET, NODE_ENV: "production" });
    const b = getEncryptionKey({ BFF_SESSION_SECRET: LONG_SECRET, NODE_ENV: "production" });
    expect(a.equals(b)).toBe(true);
  });
});

describe("verifyCsrfOrigin", () => {
  const url = "http://localhost:3000/api/bff/me/sessions/1";

  it("allows safe methods", () => {
    expect(verifyCsrfOrigin(new Request(url, { method: "GET", headers: { origin: "https://evil.example" } }))).toBe(true);
  });

  it("allows same-origin mutations", () => {
    const req = new Request(url, { method: "POST", headers: { origin: "http://localhost:3000", host: "localhost:3000" } });
    expect(verifyCsrfOrigin(req)).toBe(true);
  });

  it("blocks cross-origin mutations", () => {
    const req = new Request(url, { method: "DELETE", headers: { origin: "https://evil.example", host: "localhost:3000" } });
    expect(verifyCsrfOrigin(req)).toBe(false);
  });

  it("blocks origin-less mutations flagged as cross-site", () => {
    const req = new Request(url, { method: "POST", headers: { "sec-fetch-site": "cross-site", host: "localhost:3000" } });
    expect(verifyCsrfOrigin(req)).toBe(false);
  });

  it("blocks an unparsable origin", () => {
    const req = new Request(url, { method: "POST", headers: { origin: "null", host: "localhost:3000" } });
    expect(verifyCsrfOrigin(req)).toBe(false);
  });
});
