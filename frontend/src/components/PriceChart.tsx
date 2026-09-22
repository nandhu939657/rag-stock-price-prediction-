import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PriceBar } from "../types/db";

export function PriceChart({ bars }: { bars: PriceBar[] }) {
  if (!bars || bars.length === 0) {
    return <div className="empty-state">No price history yet — data will appear after the first analysis.</div>;
  }

  const data = bars.map((b) => ({
    ts: new Date(b.ts).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
    close: b.close,
    sma20: b.sma_20,
    bollingerUpper: b.bollinger_upper,
    bollingerLower: b.bollinger_lower,
  }));

  return (
    <div className="card">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" />
          <XAxis dataKey="ts" tick={{ fontSize: 11, fill: "var(--color-text-faint)" }} minTickGap={40} stroke="var(--color-border)" />
          <YAxis tick={{ fontSize: 11, fill: "var(--color-text-faint)" }} domain={["auto", "auto"]} stroke="var(--color-border)" />
          <Tooltip
            contentStyle={{
              background: "var(--color-surface-raised)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="close" name="Close" stroke="var(--color-accent)" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="sma20" name="SMA (20)" stroke="var(--color-warn)" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
          <Line type="monotone" dataKey="bollingerUpper" name="Bollinger upper" stroke="var(--color-hold)" strokeWidth={1} dot={false} strokeOpacity={0.6} />
          <Line type="monotone" dataKey="bollingerLower" name="Bollinger lower" stroke="var(--color-hold)" strokeWidth={1} dot={false} strokeOpacity={0.6} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
