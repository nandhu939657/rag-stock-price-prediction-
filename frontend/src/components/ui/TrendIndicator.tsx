import { TrendingUp, TrendingDown, Minus } from "lucide-react";

/** Shows recent PRICE movement, deliberately styled independent of the buy/sell/hold
 * color scheme (blue/gray tones, not green/red) - the price trend and the
 * recommendation are two different things that can legitimately disagree (e.g. a
 * stock that ran up hard can still be a "sell" if it looks overbought), and using the
 * same green/red for both would visually imply they always agree, which they don't. */
export function TrendIndicator({ returnFraction, label = "Recent trend" }: { returnFraction: number | null | undefined; label?: string }) {
  if (returnFraction == null || Number.isNaN(returnFraction)) return null;

  const pct = returnFraction * 100;
  const Icon = pct > 0.05 ? TrendingUp : pct < -0.05 ? TrendingDown : Minus;
  const color = pct > 0.05 ? "#2f6feb" : pct < -0.05 ? "#8250df" : "var(--color-text-faint)";

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12 }} title={`${label}: price change over the last ~20 bars`}>
      <Icon size={13} color={color} />
      <span style={{ color, fontWeight: 600 }}>
        {pct >= 0 ? "+" : ""}
        {pct.toFixed(2)}%
      </span>
      <span className="text-faint">{label}</span>
    </span>
  );
}
