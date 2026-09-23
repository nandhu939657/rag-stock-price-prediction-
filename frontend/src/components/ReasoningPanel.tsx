import { AlertTriangle, ShieldCheck, SearchX, BookOpen, Info, ShieldAlert, Newspaper, ExternalLink } from "lucide-react";
import type { NewsSource, Recommendation } from "../types/db";
import { RecommendationBadge, Chip } from "./ui/Badge";
import { ConfidenceGauge } from "./ui/ConfidenceGauge";
import { RiskBadge } from "./ui/RiskBadge";
import { TrendIndicator } from "./ui/TrendIndicator";
import { VerdictBanner } from "./ui/VerdictBanner";
import { FallbackNotice } from "./ui/FallbackNotice";

export function ReasoningPanel({ recommendation, sources }: { recommendation: Recommendation | null; sources?: NewsSource[] }) {
  if (!recommendation) {
    return <div className="empty-state">No recommendation yet — analyze this stock to generate one.</div>;
  }

  const snapshot = recommendation.context_snapshot;
  const hasPriceData = snapshot?.has_price_data !== false;
  const isFallback = snapshot?.is_fallback === true;
  const trendReturn = snapshot?.latest_indicators?.return_20;
  const call = recommendation.final_recommendation;

  // Price and recommendation are two different things and can legitimately disagree
  // (e.g. a stock that ran up can still be "sell" if it looks overbought) - flag it
  // explicitly rather than leaving it to look like a mistake.
  const trendDisagreesWithCall =
    trendReturn != null && ((trendReturn > 0.003 && call === "sell") || (trendReturn < -0.003 && call === "buy"));

  return (
    <div className="card" style={{ maxWidth: 860 }}>
      {!hasPriceData && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            background: "var(--color-sell-bg)",
            color: "var(--color-sell)",
            borderRadius: "var(--radius-sm)",
            padding: "9px 12px",
            fontSize: 12.5,
            marginBottom: 14,
          }}
        >
          <SearchX size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            No price or technical data was found for this symbol on the market data provider — it may be misspelled,
            delisted, or not covered (many non-US companies are only available via a US-listed ADR). The
            recommendation below is based on news context only, not real technical analysis.
          </span>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <RecommendationBadge value={recommendation.final_recommendation} />
          {snapshot?.risk_level && <RiskBadge level={snapshot.risk_level} />}
          <span className="text-faint" style={{ fontSize: 12 }}>
            {recommendation.triggered_by === "scheduled" ? "Auto-refreshed" : "On-demand"} ·{" "}
            {new Date(recommendation.created_at).toLocaleString()}
          </span>
        </div>
        <div style={{ minWidth: 140 }}>
          <ConfidenceGauge confidence={recommendation.ml_confidence} recommendation={recommendation.final_recommendation} />
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        {isFallback ? (
          <FallbackNotice reason={snapshot?.fallback_reason} />
        ) : (
          <VerdictBanner
            recommendation={recommendation.final_recommendation}
            confidence={recommendation.ml_confidence}
            riskLevel={snapshot?.risk_level}
          />
        )}
      </div>

      {trendReturn != null && (
        <div style={{ marginBottom: 14 }}>
          <TrendIndicator returnFraction={trendReturn} />
        </div>
      )}

      {trendDisagreesWithCall && (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            background: "var(--color-accent-bg)",
            color: "var(--color-accent)",
            borderRadius: "var(--radius-sm)",
            padding: "9px 12px",
            fontSize: 12.5,
            marginBottom: 14,
          }}
        >
          <Info size={15} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>
            Price and recommendation don't have to move together: this call is <strong>{call}</strong> even though
            the price has recently {trendReturn! > 0 ? "risen" : "fallen"} — see the reasoning below for why (often a
            sign the stock looks over- or under-extended relative to its recent trend, not a contradiction).
          </span>
        </div>
      )}

      {!isFallback && <p style={{ lineHeight: 1.65, marginBottom: 14, fontSize: 14 }}>{recommendation.reasoning}</p>}

      {sources && sources.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <Newspaper size={13} className="text-faint" />
            <span className="text-faint" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: 0.04, fontWeight: 600 }}>
              Based on this recent news
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sources.slice(0, 3).map((s) => (
              <div key={s.id} style={{ background: "var(--color-border-subtle)", borderRadius: "var(--radius-sm)", padding: "8px 10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 3 }}>
                  <span style={{ fontWeight: 600, fontSize: 12.5 }}>{s.title || "Untitled article"}</span>
                  <Chip>{s.source}</Chip>
                </div>
                <p className="text-muted" style={{ fontSize: 12, lineHeight: 1.5, margin: 0 }}>
                  {s.chunk_text.slice(0, 200)}
                  {s.chunk_text.length > 200 ? "…" : ""}
                </p>
                {s.source_url && (
                  <a
                    href={s.source_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 11, color: "var(--color-accent)", textDecoration: "none", marginTop: 4 }}
                  >
                    Read full article <ExternalLink size={10} />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {snapshot?.risk_factors && snapshot.risk_factors.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <ShieldAlert size={13} className="text-faint" />
            <span className="text-faint" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: 0.04, fontWeight: 600 }}>
              Risk factors
            </span>
          </div>
          {snapshot.risk_summary && (
            <p style={{ fontSize: 13, lineHeight: 1.5, margin: "0 0 6px", fontWeight: 500 }}>{snapshot.risk_summary}</p>
          )}
          <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
            {snapshot.risk_factors.map((f, i) => (
              <li key={i} className="text-muted" style={{ fontSize: 12.5, lineHeight: 1.5 }}>
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {recommendation.ml_signal && (
        <div className="text-muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
          ML signal: <strong style={{ color: "var(--color-text)" }}>{recommendation.ml_signal}</strong>
          {recommendation.ml_predicted_return != null && (
            <> · predicted move: <strong style={{ color: "var(--color-text)" }}>{(recommendation.ml_predicted_return * 100).toFixed(2)}%</strong></>
          )}
        </div>
      )}

      {!isFallback && (recommendation.context_snapshot?.strategies_considered?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <BookOpen size={13} className="text-faint" />
            <span className="text-faint" style={{ fontSize: 11.5, textTransform: "uppercase", letterSpacing: 0.04, fontWeight: 600 }}>
              Principles considered
            </span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {recommendation.context_snapshot!.strategies_considered!.map((s) => (
              <span
                key={`${s.book_title}-${s.topic}`}
                title={s.content}
                className="chip"
                style={{ cursor: "help" }}
              >
                {s.book_title} — {s.author.split(" ").slice(-1)[0]}
              </span>
            ))}
          </div>
        </div>
      )}

      {recommendation.guardrails_applied?.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <ShieldCheck size={13} className="text-faint" />
          {recommendation.guardrails_applied.map((g) => (
            <Chip key={g}>{g.replace(/_/g, " ")}</Chip>
          ))}
        </div>
      )}
    </div>
  );
}

export function DisclaimerBanner() {
  return (
    <div className="disclaimer-banner">
      <AlertTriangle size={15} style={{ flexShrink: 0 }} />
      <span>
        This tool is for personal research only and is <strong>not financial advice</strong>. Past performance
        does not guarantee future results.
      </span>
    </div>
  );
}
