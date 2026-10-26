import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export interface ApiState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  /** Re-run the request, e.g. after an action changed the data. */
  reload: () => Promise<void>;
  /** Replace the data locally with a fresh response from a POST. */
  setData: (value: T | null) => void;
}

/**
 * One small hook for every GET on the site: data, loading, error.
 * 14 endpoints do not justify a data-fetching library (TECH_STACK.md).
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const live = useRef(true);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fetcher, deps);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const value = await run();
      if (live.current) {
        setData(value);
        setError(null);
      }
    } catch (err) {
      if (live.current) {
        setError(err instanceof ApiError ? err : new ApiError(0, String(err)));
        setData(null);
      }
    } finally {
      if (live.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    live.current = true;
    void reload();
    return () => {
      live.current = false;
    };
  }, [reload]);

  return { data, error, loading, reload, setData };
}

/** For POSTs: tracks one in-flight action and its error. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  return { busy, error, run, clearError: () => setError(null) };
}
