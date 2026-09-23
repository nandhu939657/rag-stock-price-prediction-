import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import type { RiskLevel } from "../../types/db";

const CONFIG: Record<RiskLevel, { color: string; bg: string; label: string; Icon: typeof ShieldCheck }> = {
  low: { color: "var(--color-buy)", bg: "var(--color-buy-bg)", label: "Low risk", Icon: ShieldCheck },
  medium: { color: "var(--color-warn)", bg: "var(--color-warn-bg)", label: "Medium risk", Icon: ShieldQuestion },
  high: { color: "var(--color-sell)", bg: "var(--color-sell-bg)", label: "High risk", Icon: ShieldAlert },
};

export function RiskBadge({ level, compact = false }: { level: RiskLevel; compact?: boolean }) {
  const { color, bg, label, Icon } = CONFIG[level];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: compact ? "2px 8px" : "3px 10px",
        borderRadius: 999,
        fontSize: compact ? 10.5 : 11.5,
        fontWeight: 700,
        color,
        background: bg,
        textTransform: "uppercase",
        letterSpacing: 0.02,
      }}
    >
      <Icon size={compact ? 10 : 12} />
      {label}
    </span>
  );
}
