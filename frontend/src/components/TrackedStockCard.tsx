import { useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, X } from "lucide-react";
import type { TrackedStock } from "../types/db";
import { RecommendationBadge } from "./ui/Badge";
import { ConfidenceGauge } from "./ui/ConfidenceGauge";
import { Sparkline } from "./ui/Sparkline";
import { api, ApiError } from "../lib/apiClient";
import { useToast } from "./ui/Toast";

function timeAgo(iso: string | null): string {
  if (!iso) return "pending";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  return `${hours}h ago`;
}

export function TrackedStockCard({ stock, onChanged }: { stock: TrackedStock; onChanged?: () => void }) {
  const [removing, setRemoving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { push } = useToast();
  const rec = stock.latest_recommendation;

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await api.untrack(stock.ticker);
      push(`${stock.ticker} removed from watchlist`, "info");
      onChanged?.();
    } catch (e) {
      push(e instanceof ApiError ? e.message : "Failed to remove", "error");
      setRemoving(false);
    }
  };

  const handleRefresh = async (e: React.MouseEvent) => {
    e.preventDefault();
    setRefreshing(true);
    try {
      await api.analyze(stock.ticker, stock.name);
      push(`${stock.ticker} re-analyzed`, "success");
      onChanged?.();
    } catch (e) {
      push(e instanceof ApiError ? e.message : "Refresh failed", "error");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Link to={`/stock/${stock.ticker}`} className="card card-hover" style={{ display: "flex", flexDirection: "column", gap: 12, textDecoration: "none", color: "inherit" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>{stock.ticker}</div>
          <div className="text-muted" style={{ fontSize: 12 }}>{stock.name}</div>
        </div>
        {rec && <RecommendationBadge value={rec.final_recommendation} />}
      </div>

      {stock.recent_closes.length >= 2 && (
        <div>
          <Sparkline values={stock.recent_closes} />
          <div className="text-faint" style={{ fontSize: 11, marginTop: 2 }}>
            {(() => {
              const first = stock.recent_closes[0];
              const last = stock.recent_closes[stock.recent_closes.length - 1];
              const pct = ((last - first) / first) * 100;
              const sign = pct >= 0 ? "+" : "";
              return (
                <span style={{ color: pct >= 0 ? "var(--color-buy)" : "var(--color-sell)", fontWeight: 600 }}>
                  {sign}
                  {pct.toFixed(2)}%
                </span>
              );
            })()}{" "}
            recent
          </div>
        </div>
      )}

      {rec ? (
        <ConfidenceGauge confidence={rec.ml_confidence} recommendation={rec.final_recommendation} />
      ) : (
        <div className="text-muted" style={{ fontSize: 12.5 }}>Building initial analysis…</div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="text-faint" style={{ fontSize: 11 }}>Refreshed {timeAgo(stock.last_refreshed_at)}</span>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn btn-ghost btn-icon"
            title="Refresh now"
          >
            <RefreshCw size={13} className={refreshing ? "spin" : ""} />
          </button>
          <button
            onClick={(e) => {
              e.preventDefault();
              handleRemove();
            }}
            disabled={removing}
            className="btn btn-ghost btn-icon"
            title="Remove from watchlist"
            style={{ color: "var(--color-sell)" }}
          >
            <X size={13} />
          </button>
        </div>
      </div>
    </Link>
  );
}
