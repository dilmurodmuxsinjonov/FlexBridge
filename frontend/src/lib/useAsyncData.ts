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

function toError(value: unknown): Error {
  return value instanceof Error ? value : new Error(String(value));
}

/**
 * Loads data for `key` and reloads whenever the key changes. `key === null`
 * disables loading (e.g. until the user is known).
 *
 * Built for the React Compiler lint rules: no state is set synchronously in an
 * effect. A key change resets loading state during render, and the fetch result
 * is applied from the promise callback. Responses for a superseded key are
 * ignored, so a slow earlier request cannot overwrite newer data.
 */
export function useAsyncData<T>(key: string | null, fetcher: () => Promise<T>): AsyncData<T> {
  const [state, setState] = useState<InternalState<T>>({
    key,
    data: undefined,
    error: null,
    isLoading: key !== null,
  });

  if (state.key !== key) {
    // Keep the previous data while the next key loads (no flicker), but drop it
    // when loading is disabled so e.g. signed-out views never show stale data.
    setState({ key, data: key === null ? undefined : state.data, error: null, isLoading: key !== null });
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
    fetcherRef.current().then(
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
    settle(key, { isLoading: true, error: null });
    try {
      const data = await fetcherRef.current();
      settle(key, { data, error: null, isLoading: false });
    } catch (err: unknown) {
      settle(key, { error: toError(err), isLoading: false });
    }
  }, [key, settle]);

  const mutate = useCallback((updater: (current: T | undefined) => T | undefined) => {
    setState((current) => ({ ...current, data: updater(current.data) }));
  }, []);

  return { data: state.data, error: state.error, isLoading: state.isLoading, reload, mutate };
}
