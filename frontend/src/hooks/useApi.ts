import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../api/client';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * 마운트 시(그리고 deps가 바뀔 때) fetch를 실행하는 훅.
 *
 * 응답이 늦게 도착한 이전 요청이 최신 상태를 덮어쓰지 않도록 cancelled 플래그로 막는다
 * (chunk를 빠르게 연속 클릭할 때 실제로 발생한다).
 */
export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce(n => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcher()
      .then(result => { if (!cancelled) { setData(result); setLoading(false); } })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : String(e));
        setLoading(false);
      });

    return () => { cancelled = true; };
    // fetcher는 매 렌더 새 함수라 deps에 넣지 않는다 — 호출부가 실제 의존값을 넘긴다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, loading, error, reload };
}
