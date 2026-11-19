import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAuthMeCache, fetchAuthMe, loginUser, logoutUser, verifyMfa } from "./api";

const USER = { user_id: "u-1", session_id: "s-1", roles: ["STUDENT"] };

function meResponse(user: typeof USER | null = USER) {
  return new Response(JSON.stringify(user ? { ok: true, user } : { ok: false }), {
    status: user ? 200 : 401,
    headers: { "Content-Type": "application/json" },
  });
}

function okJson(body: unknown = { user_id: "u-1", roles: ["STUDENT"] }) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function meCalls(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.filter(([url]) => url === "/api/auth/me").length;
}

describe("fetchAuthMe cache", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    clearAuthMeCache();
    fetchMock = vi.fn((url: string) =>
      Promise.resolve(url === "/api/auth/me" ? meResponse() : okJson())
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.useRealTimers();
    clearAuthMeCache();
  });

  it("shares one in-flight request between simultaneous callers", async () => {
    const [a, b, c] = await Promise.all([fetchAuthMe(), fetchAuthMe(), fetchAuthMe()]);
    expect(a).toEqual(USER);
    expect(b).toEqual(USER);
    expect(c).toEqual(USER);
    expect(meCalls(fetchMock)).toBe(1);
  });

  it("reuses the answer within 5 s and refetches after it expires", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-11-17T10:00:00Z"));
    await fetchAuthMe();
    vi.setSystemTime(new Date("2026-11-17T10:00:04Z"));
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(1);
    vi.setSystemTime(new Date("2026-11-17T10:00:06Z"));
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(2);
  });

  it("force bypasses the cache", async () => {
    await fetchAuthMe();
    await fetchAuthMe({ force: true });
    expect(meCalls(fetchMock)).toBe(2);
  });

  it("is cleared by the auth-changed window event", async () => {
    await fetchAuthMe();
    window.dispatchEvent(new Event("flexbridge:auth-changed"));
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(2);
  });

  it("is cleared by login, MFA verification and logout", async () => {
    await fetchAuthMe();
    await loginUser("+998901234567", "secret");
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(2);

    await verifyMfa("ticket", "123456");
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(3);

    await logoutUser();
    await fetchAuthMe();
    expect(meCalls(fetchMock)).toBe(4);
  });

  it("does not let an older in-flight answer overwrite a newer session", async () => {
    let releaseOld: (r: Response) => void = () => {};
    fetchMock.mockImplementationOnce(
      () => new Promise<Response>((resolve) => (releaseOld = resolve))
    );
    const stale = fetchAuthMe();
    clearAuthMeCache();
    fetchMock.mockImplementationOnce(() => Promise.resolve(meResponse(null)));
    const fresh = await fetchAuthMe();
    releaseOld(meResponse());
    expect(await stale).toEqual(USER);
    expect(fresh).toBeNull();
    // The cache keeps the newer (signed-out) answer.
    expect(await fetchAuthMe()).toBeNull();
    expect(meCalls(fetchMock)).toBe(2);
  });

  it("returns null on network failure", async () => {
    fetchMock.mockImplementationOnce(() => Promise.reject(new Error("offline")));
    expect(await fetchAuthMe()).toBeNull();
  });
});
