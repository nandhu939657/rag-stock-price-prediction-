import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Mover } from "../types/db";

export function MoversChart({ movers, kind }: { movers: Mover[]; kind: "gainers" | "losers" }) {
  if (movers.length === 0) {
    return <div className="empty-state">No {kind} to show yet.</div>;
  }

  const color = kind === "gainers" ? "var(--color-buy)" : "var(--color-sell)";
  const data = [...movers].reverse().map((m) => ({ ticker: m.ticker, change: m.change_pct }));

  return (
    <div className="card">
      <ResponsiveContainer width="100%" height={Math.max(140, movers.length * 36)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <XAxis type="number" tick={{ fontSize: 11, fill: "var(--color-text-faint)" }} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="ticker" tick={{ fontSize: 12, fill: "var(--color-text)" }} width={80} />
          <Tooltip
            contentStyle={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
            formatter={(v: number) => [`${v > 0 ? "+" : ""}${v}%`, "Change"]}
          />
          <Bar dataKey="change" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.ticker} fill={color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MoversList({ movers }: { movers: Mover[] }) {
  if (movers.length === 0) {
    return <div className="empty-state">Nothing to show yet.</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {movers.map((m) => (
        <Link
          key={m.stock_id}
          to={`/stock/${m.ticker}`}
          className="card card-hover"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "center", textDecoration: "none", color: "inherit", padding: "10px 14px" }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 13.5 }}>{m.ticker}</div>
            <div className="text-muted" style={{ fontSize: 11.5 }}>{m.name}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontWeight: 700, fontSize: 13.5, color: m.change_pct >= 0 ? "var(--color-buy)" : "var(--color-sell)" }}>
              {m.change_pct >= 0 ? "+" : ""}
              {m.change_pct}%
            </div>
            <div className="text-faint" style={{ fontSize: 11 }}>{m.latest_close.toFixed(2)}</div>
          </div>
        </Link>
      ))}
    </div>
  );
}
