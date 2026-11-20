import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useAsyncData } from "./useAsyncData";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useAsyncData", () => {
  it("loads data for the initial key", async () => {
    const fetcher = vi.fn().mockResolvedValue(["a", "b"]);
    const { result } = renderHook(() => useAsyncData("k1", fetcher));

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toEqual(["a", "b"]);
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("exposes fetch errors", async () => {
    const { result } = renderHook(() => useAsyncData("k1", () => Promise.reject(new Error("boom"))));

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error?.message).toBe("boom");
  });

  it("does not load while the key is null", () => {
    const fetcher = vi.fn().mockResolvedValue(1);
    const { result } = renderHook(() => useAsyncData(null, fetcher));

    expect(result.current.isLoading).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("refetches when the key changes and ignores the superseded response", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const fetchers: Record<string, () => Promise<string>> = {
      all: () => first.promise,
      unread: () => second.promise,
    };
    const { result, rerender } = renderHook(({ k }) => useAsyncData(k, fetchers[k]), {
      initialProps: { k: "all" },
    });

    rerender({ k: "unread" });
    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      second.resolve("unread-data");
    });
    await act(async () => {
      first.resolve("stale-all-data");
    });

    expect(result.current.data).toBe("unread-data");
    expect(result.current.isLoading).toBe(false);
  });

  it("drops loaded data when the key becomes null", async () => {
    const { result, rerender } = renderHook(({ k }: { k: string | null }) => useAsyncData(k, () => Promise.resolve("private")), {
      initialProps: { k: "user-1" as string | null },
    });
    await waitFor(() => expect(result.current.data).toBe("private"));

    rerender({ k: null });

    expect(result.current.data).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
  });

  it("reload re-runs the latest fetcher and clears a previous error", async () => {
    let fail = true;
    const fetcher = vi.fn(() => (fail ? Promise.reject(new Error("offline")) : Promise.resolve("ok")));
    const { result } = renderHook(() => useAsyncData("k1", fetcher));
    await waitFor(() => expect(result.current.error?.message).toBe("offline"));

    fail = false;
    await act(async () => {
      await result.current.reload();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toBe("ok");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("mutate updates loaded data locally", async () => {
    const { result } = renderHook(() => useAsyncData("k1", () => Promise.resolve([1, 2, 3])));
    await waitFor(() => expect(result.current.data).toEqual([1, 2, 3]));

    act(() => {
      result.current.mutate((items) => items?.filter((n) => n !== 2));
    });

    expect(result.current.data).toEqual([1, 3]);
  });

  it("deduplicates concurrent requests for the same key and serves cached data in 0ms on remount", async () => {
    const pending = deferred<string[]>();
    const fetcher = vi.fn(() => pending.promise);

    const h1 = renderHook(() => useAsyncData("shared-key", fetcher));
    const h2 = renderHook(() => useAsyncData("shared-key", fetcher));

    expect(fetcher).toHaveBeenCalledTimes(1);

    await act(async () => {
      pending.resolve(["fast"]);
    });

    expect(h1.result.current.data).toEqual(["fast"]);
    expect(h2.result.current.data).toEqual(["fast"]);

    // Remounting with a cached key renders immediately in 0ms (isLoading: false, cached data present) and revalidates in background
    const h3 = renderHook(() => useAsyncData("shared-key", fetcher));
    expect(h3.result.current.isLoading).toBe(false);
    expect(h3.result.current.data).toEqual(["fast"]);
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
