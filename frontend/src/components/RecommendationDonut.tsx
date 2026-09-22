import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

interface Counts {
  buy: number;
  sell: number;
  hold: number;
}

const COLORS: Record<keyof Counts, string> = {
  buy: "var(--color-buy)",
  sell: "var(--color-sell)",
  hold: "var(--color-hold)",
};

export function RecommendationDonut({ counts }: { counts: Counts }) {
  const total = counts.buy + counts.sell + counts.hold;
  const data = (["buy", "hold", "sell"] as (keyof Counts)[])
    .map((key) => ({ name: key, value: counts[key] }))
    .filter((d) => d.value > 0);

  if (total === 0) {
    return <div className="empty-state" style={{ padding: 24 }}>No recommendations yet to chart.</div>;
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <div style={{ width: 120, height: 120, position: "relative", flexShrink: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={38} outerRadius={56} paddingAngle={2} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.name} fill={COLORS[d.name]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: "var(--color-surface-raised)", border: "1px solid var(--color-border)", borderRadius: 8, fontSize: 12 }}
              formatter={(value: number, name: string) => [`${value} stock${value === 1 ? "" : "s"}`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
            pointerEvents: "none",
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 700 }}>{total}</div>
          <div className="text-faint" style={{ fontSize: 10 }}>tracked</div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {(["buy", "hold", "sell"] as (keyof Counts)[]).map((key) => (
          <div key={key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
            <span style={{ width: 9, height: 9, borderRadius: 3, background: COLORS[key] }} />
            <span style={{ textTransform: "capitalize", minWidth: 40 }}>{key}</span>
            <strong>{counts[key]}</strong>
            <span className="text-faint">({total ? Math.round((counts[key] / total) * 100) : 0}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
