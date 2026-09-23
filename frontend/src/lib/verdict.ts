import type { RecommendationValue, RiskLevel } from "../types/db";

export interface PlainVerdict {
  headline: string;
  detail: string;
}

/** Translates the recommendation + confidence + risk into one plain-English verdict,
 * distinct from the technical reasoning and risk-factor sections. Phrasing stays soft
 * ("consider", "leaning toward") rather than commands, and never mentions specific
 * amounts or position sizes - consistent with the app's guardrails, just in simpler
 * words than the full written reasoning. */
export function getPlainVerdict(
  recommendation: RecommendationValue,
  confidence: number | null,
  riskLevel: RiskLevel | undefined
): PlainVerdict {
  const conf = confidence ?? 0;
  const strong = conf >= 0.5;
  const risky = riskLevel === "high";

  if (recommendation === "buy") {
    if (strong && !risky) {
      return {
        headline: "Leaning toward buy",
        detail: "Signals point upward with reasonable confidence, and risk looks manageable right now.",
      };
    }
    if (strong && risky) {
      return {
        headline: "Leaning toward buy, but stay cautious",
        detail: "Signals point upward, but conditions are volatile - going in gradually or waiting for confirmation may be wiser than all at once.",
      };
    }
    return {
      headline: "Mild lean toward buy",
      detail: "There's a slight upward lean, but the signal isn't strong enough to act on with much confidence.",
    };
  }

  if (recommendation === "sell") {
    if (strong && !risky) {
      return {
        headline: "Leaning toward sell",
        detail: "Signals point downward with reasonable confidence, and the picture is fairly clear.",
      };
    }
    if (strong && risky) {
      return {
        headline: "Leaning toward sell, but stay cautious",
        detail: "Signals point downward, and conditions are volatile - reducing gradually or waiting for confirmation may be wiser than all at once.",
      };
    }
    return {
      headline: "Mild lean toward sell",
      detail: "There's a slight downward lean, but the signal isn't strong enough to act on with much confidence.",
    };
  }

  // hold
  if (risky) {
    return {
      headline: "Hold - but check back soon",
      detail: "No clear buy or sell signal right now, and conditions are volatile enough that it's worth another look soon.",
    };
  }
  return {
    headline: "Hold - no action needed",
    detail: "No strong reason to buy more or sell right now. Sitting tight and keeping watch looks like the reasonable move.",
  };
}
