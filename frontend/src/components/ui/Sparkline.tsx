import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";

export function Sparkline({ values, height = 36 }: { values: number[]; height?: number }) {
  if (!values || values.length < 2) {
    return <div className="text-faint" style={{ fontSize: 11, height }}>Not enough data yet</div>;
  }

  const data = values.map((v, i) => ({ i, v }));
  const trendingUp = values[values.length - 1] >= values[0];
  const color = trendingUp ? "var(--color-buy)" : "var(--color-sell)";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <YAxis domain={["dataMin", "dataMax"]} hide />
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.75} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
