-- Master stock list
create table if not exists stocks (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  name text not null,
  exchange text,
  sector text,
  created_at timestamptz not null default now()
);

-- Watchlist / tracking state
create table if not exists tracked_stocks (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references stocks(id) on delete cascade,
  is_tracked boolean not null default true,
  added_at timestamptz not null default now(),
  removed_at timestamptz,
  last_refreshed_at timestamptz,
  unique (stock_id)
);

create index if not exists idx_tracked_stocks_is_tracked on tracked_stocks (is_tracked);
