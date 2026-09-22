-- Single-user app: RLS enabled with read-only access for the anon key.
-- All writes go through the backend using the service_role key, which bypasses RLS.

alter table stocks enable row level security;
alter table tracked_stocks enable row level security;
alter table price_history enable row level security;
alter table knowledge_base enable row level security;
alter table document_chunks enable row level security;
alter table recommendations enable row level security;

create policy "anon can read stocks" on stocks for select using (true);
create policy "anon can read tracked_stocks" on tracked_stocks for select using (true);
create policy "anon can read price_history" on price_history for select using (true);
create policy "anon can read recommendations" on recommendations for select using (true);
-- knowledge_base and document_chunks are backend-internal (guardrails + RAG corpus); no anon read policy.

-- Enable realtime so the frontend dashboard updates live without polling.
alter publication supabase_realtime add table tracked_stocks;
alter publication supabase_realtime add table recommendations;
