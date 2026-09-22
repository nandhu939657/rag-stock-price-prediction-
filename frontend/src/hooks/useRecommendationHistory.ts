import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { api } from "../lib/apiClient";
import type { StockHistory } from "../types/db";

/** Price + recommendation history for one stock's detail page, refreshed live whenever
 * a new recommendation lands for this stock's stock_id. */
export function useRecommendationHistory(ticker: string | undefined) {
  const [data, setData] = useState<StockHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!ticker) return;
    try {
      const result = await api.history(ticker);
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    setLoading(true);
    refresh();

    if (!ticker) return;
    const stockId = data?.recommendations?.[0]?.stock_id;

    const channel = supabase
      .channel(`recommendation-history-${ticker}`)
      .on(
        "postgres_changes",
        stockId
          ? { event: "*", schema: "public", table: "recommendations", filter: `stock_id=eq.${stockId}` }
          : { event: "*", schema: "public", table: "recommendations" },
        () => refresh()
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, refresh]);

  return { data, loading, error, refresh };
}
