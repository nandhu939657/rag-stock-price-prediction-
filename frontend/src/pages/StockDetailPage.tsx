import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, RefreshCw, XCircle } from "lucide-react";
import { useRecommendationHistory } from "../hooks/useRecommendationHistory";
import { PriceChart } from "../components/PriceChart";
import { IndicatorPanel } from "../components/IndicatorPanel";
import { ReasoningPanel, DisclaimerBanner } from "../components/ReasoningPanel";
import { HistoryTable } from "../components/HistoryTable";
import { NewsSourceCard } from "../components/NewsSourceCard";
import { AddToWatchlistButton } from "../components/AddToWatchlistButton";
import { api, ApiError } from "../lib/apiClient";
import { useToast } from "../components/ui/Toast";

type Tab = "overview" | "sources" | "history";

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error, refresh } = useRecommendationHistory(ticker);
  const [tab, setTab] = useState<Tab>("overview");
  const [untracking, setUntracking] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { push } = useToast();

  const latestBar = data?.price_history[data.price_history.length - 1];
  const latestRecommendation = data?.recommendations[0] ?? null;

  const handleUntrack = async () => {
    if (!ticker) return;
    setUntracking(true);
    try {
      await api.untrack(ticker);
      push(`${ticker} removed from watchlist`, "info");
    } catch (e) {
      push(e instanceof ApiError ? e.message : "Failed to remove", "error");
    } finally {
      setUntracking(false);
    }
  };

  const handleRefresh = async () => {
    if (!ticker) return;
    setRefreshing(true);
    try {
      await api.analyze(ticker);
      push(`${ticker} re-analyzed`, "success");
      refresh();
    } catch (e) {
      push(e instanceof ApiError ? e.message : "Refresh failed", "error");
    } finally {
      setRefreshing(false);
    }
  };

  if (!ticker) return null;

  return (
    <div>
      <DisclaimerBanner />

      <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12.5, color: "var(--color-accent)", textDecoration: "none", marginBottom: 8 }}>
        <ArrowLeft size={13} /> Dashboard
      </Link>

      <div className="page-header">
        <h1 className="page-title">{ticker}</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={handleRefresh} disabled={refreshing} className="btn btn-secondary">
            <RefreshCw size={14} className={refreshing ? "spin" : ""} /> Refresh now
          </button>
          <AddToWatchlistButton ticker={ticker} onTracked={refresh} />
          <button onClick={handleUntrack} disabled={untracking} className="btn btn-danger-ghost">
            <XCircle size={14} /> Stop tracking
          </button>
        </div>
      </div>

      {loading && <div className="empty-state">Loading…</div>}
      {error && <div className="empty-state" style={{ borderColor: "var(--color-sell)", color: "var(--color-sell)" }}>{error}</div>}

      {data && (
        <>
          <div className="tabs">
            <button className={`tab ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}>
              Overview
            </button>
            <button className={`tab ${tab === "sources" ? "active" : ""}`} onClick={() => setTab("sources")}>
              News &amp; Sources {data.sources.length > 0 && `(${data.sources.length})`}
            </button>
            <button className={`tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
              History {data.recommendations.length > 0 && `(${data.recommendations.length})`}
            </button>
          </div>

          {tab === "overview" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
              <section>
                <h2 className="kicker">Price</h2>
                <PriceChart bars={data.price_history} />
              </section>
              <section>
                <h2 className="kicker">Indicators</h2>
                <IndicatorPanel latest={latestBar} />
              </section>
              <section>
                <h2 className="kicker">Latest recommendation</h2>
                <ReasoningPanel recommendation={latestRecommendation} />
              </section>
            </div>
          )}

          {tab === "sources" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {data.sources.length === 0 ? (
                <div className="empty-state">
                  No news retrieved yet for this stock. Sources refresh roughly hourly once tracked, or immediately on
                  the next "Refresh now".
                </div>
              ) : (
                data.sources.map((s) => <NewsSourceCard key={s.id} source={s} />)
              )}
            </div>
          )}

          {tab === "history" && <HistoryTable recommendations={data.recommendations} />}
        </>
      )}
    </div>
  );
}
