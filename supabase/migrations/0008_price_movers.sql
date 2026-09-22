-- Returns the latest vs previous close (and % change) for every stock that has at
-- least 2 price_history bars, used to power the "Top Movers" overview. Scoped to
-- stocks that have actually been analyzed in this app (not a full market scan).
create or replace function get_price_movers()
returns table (
  stock_id uuid,
  ticker text,
  name text,
  latest_close numeric,
  previous_close numeric,
  change_pct numeric,
  latest_ts timestamptz
)
language sql stable
as $$
  with ranked as (
    select
      ph.stock_id,
      ph.close,
      ph.ts,
      row_number() over (partition by ph.stock_id order by ph.ts desc) as rn
    from price_history ph
    where ph.close is not null
  )
  select
    s.id as stock_id,
    s.ticker,
    s.name,
    latest.close as latest_close,
    prev.close as previous_close,
    case when prev.close > 0 then round(((latest.close - prev.close) / prev.close) * 100, 2) else null end as change_pct,
    latest.ts as latest_ts
  from stocks s
  join ranked latest on latest.stock_id = s.id and latest.rn = 1
  join ranked prev on prev.stock_id = s.id and prev.rn = 2
  where prev.close is not null and prev.close > 0
  order by change_pct desc nulls last;
$$;

-- Compact recent-close history per stock, for sparklines on the watchlist dashboard.
create or replace function get_recent_closes(target_stock_id uuid, bar_count int default 12)
returns table (ts timestamptz, close numeric)
language sql stable
as $$
  select ph.ts, ph.close
  from price_history ph
  where ph.stock_id = target_stock_id and ph.close is not null
  order by ph.ts desc
  limit bar_count;
$$;
