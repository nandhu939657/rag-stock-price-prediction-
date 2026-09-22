-- Prediction/decision audit trail: every buy/sell/hold call ever made, with reasoning
create table if not exists recommendations (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid not null references stocks(id) on delete cascade,
  created_at timestamptz not null default now(),
  ml_signal text check (ml_signal in ('up', 'down', 'flat')),
  ml_predicted_return numeric,
  ml_confidence numeric,
  final_recommendation text not null check (final_recommendation in ('buy', 'sell', 'hold')),
  reasoning text not null,
  guardrails_applied text[] not null default '{}',
  context_snapshot jsonb,
  triggered_by text not null default 'scheduled' check (triggered_by in ('scheduled', 'on_demand'))
);

create index if not exists idx_recommendations_stock_created on recommendations (stock_id, created_at desc);
