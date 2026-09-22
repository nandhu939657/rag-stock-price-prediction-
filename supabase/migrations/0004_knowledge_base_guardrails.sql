-- Guardrail rules and general domain knowledge (structured, injected verbatim into LLM prompts)
create table if not exists knowledge_base (
  id uuid primary key default gen_random_uuid(),
  category text not null check (category in ('guardrail', 'domain_fact')),
  rule_key text not null,
  content text not null,
  severity text not null default 'hard' check (severity in ('hard', 'soft')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (rule_key)
);

create index if not exists idx_knowledge_base_active on knowledge_base (category, is_active);
