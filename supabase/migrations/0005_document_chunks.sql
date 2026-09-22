-- RAG corpus: scraped news/article chunks with embeddings (all-MiniLM-L6-v2, 384 dims)
create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  stock_id uuid references stocks(id) on delete cascade,
  source text not null check (source in ('firecrawl', 'apify')),
  source_url text,
  title text,
  published_at timestamptz,
  chunk_text text not null,
  chunk_index int not null default 0,
  embedding vector(384),
  scraped_at timestamptz not null default now()
);

create index if not exists idx_document_chunks_stock_scraped on document_chunks (stock_id, scraped_at desc);

-- ivfflat needs rows + an ANALYZE to be effective; fine to create early, effectiveness improves with data volume.
create index if not exists idx_document_chunks_embedding on document_chunks
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- RPC used by the backend for pgvector similarity search, scoped to one stock.
create or replace function match_document_chunks(
  query_embedding vector(384),
  target_stock_id uuid,
  match_count int default 5
)
returns table (
  id uuid,
  chunk_text text,
  source_url text,
  title text,
  published_at timestamptz,
  similarity float
)
language sql stable
as $$
  select
    document_chunks.id,
    document_chunks.chunk_text,
    document_chunks.source_url,
    document_chunks.title,
    document_chunks.published_at,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where document_chunks.stock_id = target_stock_id
    and document_chunks.embedding is not null
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;
