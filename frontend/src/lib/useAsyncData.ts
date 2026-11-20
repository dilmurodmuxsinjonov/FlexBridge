"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncDataState<T> {
  data: T | undefined;
  error: Error | null;
  isLoading: boolean;
}

export interface AsyncData<T> extends AsyncDataState<T> {
  /** Re-runs the fetcher for the current key (for refresh buttons and after mutations). */
  reload: () => Promise<void>;
  /** Locally updates loaded data, e.g. after an optimistic removal. */
  mutate: (updater: (current: T | undefined) => T | undefined) => void;
}

interface InternalState<T> extends AsyncDataState<T> {
  key: string | null;
}

interface CacheEntry {
  data: unknown;
  at: number;
}

const CACHE_TTL_MS = 30_000;
const MAX_CACHE_ENTRIES = 120;

const cacheMap = new Map<string, CacheEntry>();
const inFlightMap = new Map<string, Promise<unknown>>();
let cacheGeneration = 0;

/** Drop all cached & in-flight `useAsyncData` entries (called automatically on auth change). */
export function clearAsyncDataCache(): void {
  cacheGeneration += 1;
  cacheMap.clear();
  inFlightMap.clear();
}

if (typeof window !== "undefined") {
  window.addEventListener("flexbridge:auth-changed", clearAsyncDataCache);
}

function readCached<T>(key: string | null): { data: T } | undefined {
  if (key === null) return undefined;
  const entry = cacheMap.get(key);
  if (!entry) return undefined;
  if (Date.now() - entry.at > CACHE_TTL_MS) {
    cacheMap.delete(key);
    return undefined;
  }
  return { data: entry.data as T };
}

function writeCached(key: string, data: unknown): void {
  if (cacheMap.size >= MAX_CACHE_ENTRIES && !cacheMap.has(key)) {
    const oldestKey = cacheMap.keys().next().value;
    if (oldestKey !== undefined) cacheMap.delete(oldestKey);
  }
  cacheMap.set(key, { data, at: Date.now() });
}

function runDeduplicated<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inFlightMap.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  const gen = cacheGeneration;
  const promise = fn().then(
    (data) => {
      if (gen === cacheGeneration) {
        writeCached(key, data);
      }
      inFlightMap.delete(key);
      return data;
    },
    (err: unknown) => {
      inFlightMap.delete(key);
      throw err;
    }
  );
  inFlightMap.set(key, promise);
  return promise;
}

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}

/**
 * Loads data for `key` and reloads whenever the key changes. `key === null`
 * disables loading (e.g. until the user is known).
 *
 * Includes in-flight request deduplication and a short-lived Stale-While-Revalidate
 * memory cache (automatically cleared on `flexbridge:auth-changed`) so revisiting
 * a recently loaded tab or filter key renders in 0ms without spinner flicker while
 * refreshing in the background.
 */
export function useAsyncData<T>(key: string | null, fetcher: () => Promise<T>): AsyncData<T> {
  const [state, setState] = useState<InternalState<T>>(() => {
    const cached = readCached<T>(key);
    if (cached !== undefined) {
      return {
        key,
        data: cached.data,
        error: null,
        isLoading: false,
      };
    }
    return {
      key,
      data: undefined,
      error: null,
      isLoading: key !== null,
    };
  });

  if (state.key !== key) {
    const cached = readCached<T>(key);
    if (cached !== undefined) {
      setState({
        key,
        data: cached.data,
        error: null,
        isLoading: false,
      });
    } else {
      // Keep the previous data while the next key loads (no layout collapse),
      // but drop it when loading is disabled so signed-out views never show stale data.
      setState({ key, data: key === null ? undefined : state.data, error: null, isLoading: key !== null });
    }
  }

  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const settle = useCallback((forKey: string, patch: Partial<AsyncDataState<T>>) => {
    setState((current) => (current.key === forKey ? { ...current, ...patch } : current));
  }, []);

  useEffect(() => {
    if (key === null) return;
    let active = true;
    runDeduplicated(key, () => fetcherRef.current()).then(
      (data) => {
        if (active) settle(key, { data, error: null, isLoading: false });
      },
      (err: unknown) => {
        if (active) settle(key, { error: toError(err), isLoading: false });
      }
    );
    return () => {
      active = false;
    };
  }, [key, settle]);

  const reload = useCallback(async () => {
    if (key === null) return;
    cacheMap.delete(key);
    inFlightMap.delete(key);
    settle(key, { isLoading: true, error: null });
    try {
      const data = await runDeduplicated(key, () => fetcherRef.current());
      settle(key, { data, error: null, isLoading: false });
    } catch (err: unknown) {
      settle(key, { error: toError(err), isLoading: false });
    }
  }, [key, settle]);

  const mutate = useCallback((updater: (current: T | undefined) => T | undefined) => {
    setState((current) => {
      const nextData = updater(current.data);
      if (current.key !== null) {
        if (nextData === undefined) cacheMap.delete(current.key);
        else writeCached(current.key, nextData);
      }
      return { ...current, data: nextData };
    });
  }, []);

  return { data: state.data, error: state.error, isLoading: state.isLoading, reload, mutate };
}
