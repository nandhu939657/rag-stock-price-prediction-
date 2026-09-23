import { TrendingUp, TrendingDown, PauseCircle } from "lucide-react";
import type { RecommendationValue, RiskLevel } from "../../types/db";
import { getPlainVerdict } from "../../lib/verdict";

const STYLE: Record<RecommendationValue, { color: string; bg: string; Icon: typeof TrendingUp }> = {
  buy: { color: "var(--color-buy)", bg: "var(--color-buy-bg)", Icon: TrendingUp },
  sell: { color: "var(--color-sell)", bg: "var(--color-sell-bg)", Icon: TrendingDown },
  hold: { color: "var(--color-hold)", bg: "var(--color-hold-bg)", Icon: PauseCircle },
};

export function VerdictBanner({
  recommendation,
  confidence,
  riskLevel,
  compact = false,
}: {
  recommendation: RecommendationValue;
  confidence: number | null;
  riskLevel: RiskLevel | undefined;
  compact?: boolean;
}) {
  const verdict = getPlainVerdict(recommendation, confidence, riskLevel);
  const { color, bg, Icon } = STYLE[recommendation];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        background: bg,
        borderRadius: "var(--radius-md)",
        padding: compact ? "10px 12px" : "12px 14px",
      }}
    >
      <Icon size={compact ? 16 : 20} color={color} style={{ flexShrink: 0, marginTop: 1 }} />
      <div>
        <div style={{ fontWeight: 700, fontSize: compact ? 13 : 14.5, color }}>{verdict.headline}</div>
        <div style={{ fontSize: compact ? 11.5 : 12.5, lineHeight: 1.4, color, opacity: 0.9, marginTop: 2 }}>{verdict.detail}</div>
      </div>
    </div>
  );
}
