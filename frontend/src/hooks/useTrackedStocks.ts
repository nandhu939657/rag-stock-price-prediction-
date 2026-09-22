import { useCallback, useEffect, useState } from "react";
import { supabase } from "../lib/supabaseClient";
import { api } from "../lib/apiClient";
import type { TrackedStock } from "../types/db";

/** Tracked watchlist + latest recommendation each, kept live via Supabase realtime
 * subscriptions on tracked_stocks and recommendations - no frontend polling needed. */
export function useTrackedStocks() {
  const [stocks, setStocks] = useState<TrackedStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listTracked();
      setStocks(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tracked stocks");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();

    const channel = supabase
      .channel("tracked-stocks-watch")
      .on("postgres_changes", { event: "*", schema: "public", table: "tracked_stocks" }, () => refresh())
      .on("postgres_changes", { event: "*", schema: "public", table: "recommendations" }, () => refresh())
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [refresh]);

  return { stocks, loading, error, refresh };
}
