-- Strategy/principle knowledge base, inspired by well-known investing and trading
-- books - distinct from document_chunks (which holds time-sensitive scraped news).
-- This is timeless reference material, retrieved via RAG based on the CURRENT
-- technical/ML situation for a stock (e.g. "oversold, low volatility, bullish MACD"),
-- so the Groq prompt gets principles actually relevant to what's happening right now
-- rather than a fixed dump of every strategy on every call.
create table if not exists strategy_knowledge (
  id uuid primary key default gen_random_uuid(),
  book_title text not null,
  author text not null,
  topic text not null,  -- e.g. 'value_investing', 'momentum', 'risk_management'
  content text not null,  -- original summary of the principle, not verbatim book text
  embedding vector(384),
  created_at timestamptz not null default now()
);

create index if not exists idx_strategy_knowledge_embedding on strategy_knowledge
  using ivfflat (embedding vector_cosine_ops) with (lists = 50);

create index if not exists idx_strategy_knowledge_topic on strategy_knowledge (topic);

-- RAG similarity search over strategy knowledge, mirroring match_document_chunks.
create or replace function match_strategy_knowledge(
  query_embedding vector(384),
  match_count int default 4
)
returns table (
  id uuid,
  book_title text,
  author text,
  topic text,
  content text,
  similarity float
)
language sql stable
as $$
  select
    strategy_knowledge.id,
    strategy_knowledge.book_title,
    strategy_knowledge.author,
    strategy_knowledge.topic,
    strategy_knowledge.content,
    1 - (strategy_knowledge.embedding <=> query_embedding) as similarity
  from strategy_knowledge
  where strategy_knowledge.embedding is not null
  order by strategy_knowledge.embedding <=> query_embedding
  limit match_count;
$$;

-- Readable, anon-key access (like knowledge_base) so the Settings page can show the
-- book library; all writes still go through the backend's service_role key.
alter table strategy_knowledge enable row level security;
create policy "anon can read strategy_knowledge" on strategy_knowledge for select using (true);
