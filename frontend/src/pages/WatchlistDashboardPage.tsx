import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Plus, TrendingUp, TrendingDown, Minus, ListChecks } from "lucide-react";
import { useTrackedStocks } from "../hooks/useTrackedStocks";
import { TrackedStockCard } from "../components/TrackedStockCard";
import { CardSkeleton } from "../components/ui/Skeleton";
import { DisclaimerBanner } from "../components/ReasoningPanel";
import { RecommendationDonut } from "../components/RecommendationDonut";
import type { RecommendationValue, TrackedStock } from "../types/db";

type Filter = "all" | RecommendationValue;
type SortKey = "recent" | "confidence" | "name";

function StatTile({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return (
    <div className="stat-tile" style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div>{icon}</div>
      <div>
        <div className="stat-tile-label">{label}</div>
        <div className="stat-tile-value">{value}</div>
      </div>
    </div>
  );
}

function sortStocks(stocks: TrackedStock[], key: SortKey): TrackedStock[] {
  const copy = [...stocks];
  if (key === "name") return copy.sort((a, b) => a.ticker.localeCompare(b.ticker));
  if (key === "confidence")
    return copy.sort((a, b) => (b.latest_recommendation?.ml_confidence ?? -1) - (a.latest_recommendation?.ml_confidence ?? -1));
  return copy.sort(
    (a, b) => new Date(b.latest_recommendation?.created_at ?? 0).getTime() - new Date(a.latest_recommendation?.created_at ?? 0).getTime()
  );
}

export function WatchlistDashboardPage() {
  const { stocks, loading, error, refresh } = useTrackedStocks();
  const [filter, setFilter] = useState<Filter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("recent");

  const counts = useMemo(() => {
    const c = { buy: 0, sell: 0, hold: 0 };
    for (const s of stocks) {
      const rec = s.latest_recommendation?.final_recommendation;
      if (rec) c[rec]++;
    }
    return c;
  }, [stocks]);

  const visible = useMemo(() => {
    const filtered = filter === "all" ? stocks : stocks.filter((s) => s.latest_recommendation?.final_recommendation === filter);
    return sortStocks(filtered, sortKey);
  }, [stocks, filter, sortKey]);

  return (
    <div>
      <DisclaimerBanner />

      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Your tracked stocks, refreshed automatically every 5 minutes.</p>
        </div>
        <Link to="/search" className="btn btn-primary">
          <Plus size={14} /> Analyze a stock
        </Link>
      </div>

      {!loading && stocks.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, marginBottom: 24, alignItems: "stretch" }}>
          <div className="stat-row" style={{ marginBottom: 0 }}>
            <StatTile label="Tracked" value={stocks.length} icon={<ListChecks size={18} color="var(--color-accent)" />} />
            <StatTile label="Buy calls" value={counts.buy} icon={<TrendingUp size={18} color="var(--color-buy)" />} />
            <StatTile label="Sell calls" value={counts.sell} icon={<TrendingDown size={18} color="var(--color-sell)" />} />
            <StatTile label="Hold calls" value={counts.hold} icon={<Minus size={18} color="var(--color-hold)" />} />
          </div>
          <div className="card" style={{ display: "flex", alignItems: "center" }}>
            <RecommendationDonut counts={counts} />
          </div>
        </div>
      )}

      {error && (
        <div className="empty-state" style={{ borderColor: "var(--color-sell)", color: "var(--color-sell)", marginBottom: 16 }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {[0, 1, 2].map((i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      )}

      {!loading && stocks.length === 0 && (
        <div className="empty-state">
          No stocks tracked yet. <Link to="/search" style={{ color: "var(--color-accent)" }}>Search for one</Link> and add it to your
          watchlist.
        </div>
      )}

      {!loading && stocks.length > 0 && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
            <div style={{ display: "flex", gap: 6 }}>
              {(["all", "buy", "sell", "hold"] as Filter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`btn btn-sm ${filter === f ? "btn-primary" : "btn-secondary"}`}
                  style={{ textTransform: "capitalize" }}
                >
                  {f}
                </button>
              ))}
            </div>
            <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)} className="input" style={{ width: "auto" }}>
              <option value="recent">Sort: Recently updated</option>
              <option value="confidence">Sort: Confidence</option>
              <option value="name">Sort: Name</option>
            </select>
          </div>

          {visible.length === 0 ? (
            <div className="empty-state">No stocks match this filter.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {visible.map((s) => (
                <TrackedStockCard key={s.stock_id} stock={s} onChanged={refresh} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
