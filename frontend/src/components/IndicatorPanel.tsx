import type { PriceBar } from "../types/db";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-faint" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.04, marginBottom: 3 }}>
        {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

export function IndicatorPanel({ latest }: { latest: PriceBar | undefined }) {
  if (!latest) {
    return <div className="empty-state">Not enough price history yet.</div>;
  }

  const fmt = (v: number | null | undefined, digits = 2) => (v == null ? "—" : v.toFixed(digits));

  return (
    <div className="card" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 18 }}>
      <Stat label="Close" value={fmt(latest.close)} />
      <Stat label="RSI (14)" value={fmt(latest.rsi_14)} />
      <Stat label="MACD" value={fmt(latest.macd, 4)} />
      <Stat label="MACD signal" value={fmt(latest.macd_signal, 4)} />
      <Stat label="SMA (20)" value={fmt(latest.sma_20)} />
      <Stat label="EMA (20)" value={fmt(latest.ema_20)} />
      <Stat label="Bollinger upper" value={fmt(latest.bollinger_upper)} />
      <Stat label="Bollinger lower" value={fmt(latest.bollinger_lower)} />
    </div>
  );
}
