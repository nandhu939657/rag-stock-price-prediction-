import { useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, X, ShieldAlert, MessageSquareText, Gauge, Lightbulb } from "lucide-react";
import type { TrackedStock } from "../types/db";
import { RecommendationBadge, Chip } from "./ui/Badge";
import { ConfidenceGauge } from "./ui/ConfidenceGauge";
import { RiskBadge } from "./ui/RiskBadge";
import { Sparkline } from "./ui/Sparkline";
import { VerdictBanner } from "./ui/VerdictBanner";
import { FallbackNotice } from "./ui/FallbackNotice";
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

function SectionLabel({ icon: Icon, children }: { icon: typeof Gauge; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
      <Icon size={13} className="text-faint" />
      <span className="text-faint" style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: 0.05, fontWeight: 700 }}>
        {children}
      </span>
    </div>
  );
}

export function TrackedStockCard({ stock, onChanged }: { stock: TrackedStock; onChanged?: () => void }) {
  const [removing, setRemoving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { push } = useToast();
  const rec = stock.latest_recommendation;
  const snapshot = rec?.context_snapshot;
  const isFallback = snapshot?.is_fallback === true;

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
    <Link to={`/stock/${stock.ticker}`} className="card card-hover" style={{ display: "block", textDecoration: "none", color: "inherit", padding: 20 }}>
      <div className="tracked-card-grid">
        {/* Section 1: overview - identity, price trend, confidence, actions */}
        <div className="tracked-card-section" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{stock.ticker}</div>
            <div className="text-muted" style={{ fontSize: 12.5 }}>{stock.name}</div>
          </div>

          {stock.recent_closes.length >= 2 && (
            <div>
              <Sparkline values={stock.recent_closes} height={44} />
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

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto" }}>
            <span className="text-faint" style={{ fontSize: 11 }}>Refreshed {timeAgo(stock.last_refreshed_at)}</span>
            <div style={{ display: "flex", gap: 4 }}>
              <button onClick={handleRefresh} disabled={refreshing} className="btn btn-ghost btn-icon" title="Refresh now">
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
        </div>

        {/* Section 2: plain-words verdict - a simple, non-technical quick take */}
        <div className="tracked-card-section">
          <SectionLabel icon={Lightbulb}>What to do</SectionLabel>
          {!rec ? (
            <div className="text-muted" style={{ fontSize: 12.5 }}>No recommendation yet.</div>
          ) : isFallback ? (
            <FallbackNotice reason={snapshot?.fallback_reason} compact />
          ) : (
            <VerdictBanner
              recommendation={rec.final_recommendation}
              confidence={rec.ml_confidence}
              riskLevel={snapshot?.risk_level}
              compact
            />
          )}
        </div>

        {/* Section 3: the buy/sell/hold call and its technical reasoning */}
        <div className="tracked-card-section">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <SectionLabel icon={MessageSquareText}>Reasoning</SectionLabel>
            {rec && <RecommendationBadge value={rec.final_recommendation} />}
          </div>
          {!rec ? (
            <div className="text-muted" style={{ fontSize: 12.5 }}>No recommendation yet.</div>
          ) : isFallback ? (
            <div className="text-faint" style={{ fontSize: 12.5 }}>No real analysis this cycle — see note above.</div>
          ) : (
            <p className="text-muted" style={{ fontSize: 13, lineHeight: 1.55, margin: 0 }}>
              {rec.reasoning}
            </p>
          )}
        </div>

        {/* Section 4: risk factor reasoning */}
        <div className="tracked-card-section">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <SectionLabel icon={ShieldAlert}>Risk factor</SectionLabel>
            {snapshot?.risk_level && <RiskBadge level={snapshot.risk_level} compact />}
          </div>
          {snapshot?.risk_summary ? (
            <>
              <p style={{ fontSize: 12.5, lineHeight: 1.5, margin: "0 0 8px", fontWeight: 500 }}>{snapshot.risk_summary}</p>
              {snapshot.risk_factors && snapshot.risk_factors.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 16, display: "flex", flexDirection: "column", gap: 4 }}>
                  {snapshot.risk_factors.map((f, i) => (
                    <li key={i} className="text-muted" style={{ fontSize: 11.5, lineHeight: 1.45 }}>
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <div className="text-muted" style={{ fontSize: 12.5 }}>No risk assessment yet.</div>
          )}
          {rec?.guardrails_applied && rec.guardrails_applied.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 10 }}>
              {rec.guardrails_applied.slice(0, 3).map((g) => (
                <Chip key={g}>{g.replace(/_/g, " ")}</Chip>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
