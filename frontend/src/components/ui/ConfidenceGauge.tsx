import type { RecommendationValue } from "../../types/db";

const COLOR_VAR: Record<RecommendationValue, string> = {
  buy: "var(--color-buy)",
  sell: "var(--color-sell)",
  hold: "var(--color-hold)",
};

export function ConfidenceGauge({
  confidence,
  recommendation,
  showLabel = true,
}: {
  confidence: number | null;
  recommendation: RecommendationValue;
  showLabel?: boolean;
}) {
  const pct = confidence != null ? Math.round(Math.max(0, Math.min(1, confidence)) * 100) : 0;
  const color = COLOR_VAR[recommendation];

  return (
    <div>
      {showLabel && (
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 11.5 }}>
          <span className="text-faint">Confidence</span>
          <span style={{ fontWeight: 600 }}>{confidence != null ? `${pct}%` : "n/a"}</span>
        </div>
      )}
      <div className="gauge-track">
        <div className="gauge-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
