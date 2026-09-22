-- OHLCV + computed technical indicators, one row per stock per bar
create table if not exists price_history (
  id bigint generated always as identity primary key,
  stock_id uuid not null references stocks(id) on delete cascade,
  ts timestamptz not null,
  open numeric,
  high numeric,
  low numeric,
  close numeric,
  volume bigint,
  sma_20 numeric,
  ema_20 numeric,
  rsi_14 numeric,
  macd numeric,
  macd_signal numeric,
  macd_hist numeric,
  bollinger_upper numeric,
  bollinger_lower numeric,
  bollinger_mid numeric,
  volatility_20 numeric,
  created_at timestamptz not null default now(),
  unique (stock_id, ts)
);

create index if not exists idx_price_history_stock_ts on price_history (stock_id, ts desc);
