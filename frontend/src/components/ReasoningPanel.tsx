import { AlertTriangle, ShieldCheck, SearchX, BookOpen } from "lucide-react";
import type { Recommendation } from "../types/db";
import { RecommendationBadge, Chip } from "./ui/Badge";
import { ConfidenceGauge } from "./ui/ConfidenceGauge";

export function ReasoningPanel({ recommendation }: { recommendation: Recommendation | null }) {
  if (!recommendation) {
    return <div className="empty-state">No recommendation yet — analyze this stock to generate one.</div>;
  }

  const hasPriceData = recommendation.context_snapshot?.has_price_data !== false;

  return (
    <div className="card">
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

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <RecommendationBadge value={recommendation.final_recommendation} />
          <span className="text-faint" style={{ fontSize: 12 }}>
            {recommendation.triggered_by === "scheduled" ? "Auto-refreshed" : "On-demand"} ·{" "}
            {new Date(recommendation.created_at).toLocaleString()}
          </span>
        </div>
        <div style={{ minWidth: 140 }}>
          <ConfidenceGauge confidence={recommendation.ml_confidence} recommendation={recommendation.final_recommendation} />
        </div>
      </div>

      <p style={{ lineHeight: 1.65, marginBottom: 14, fontSize: 14 }}>{recommendation.reasoning}</p>

      {recommendation.ml_signal && (
        <div className="text-muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
          ML signal: <strong style={{ color: "var(--color-text)" }}>{recommendation.ml_signal}</strong>
          {recommendation.ml_predicted_return != null && (
            <> · predicted move: <strong style={{ color: "var(--color-text)" }}>{(recommendation.ml_predicted_return * 100).toFixed(2)}%</strong></>
          )}
        </div>
      )}

      {(recommendation.context_snapshot?.strategies_considered?.length ?? 0) > 0 && (
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
