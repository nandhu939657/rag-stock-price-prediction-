-- Initial guardrail rules enforced on every Groq recommendation.
insert into knowledge_base (category, rule_key, content, severity, is_active) values
  ('guardrail', 'mandatory_disclaimer',
   'Always explicitly state that this is not financial advice and that past performance does not guarantee future results.',
   'hard', true),
  ('guardrail', 'no_leverage_recommendation',
   'Never recommend margin trading, options, futures, or any leveraged instrument.',
   'hard', true),
  ('guardrail', 'confidence_cap',
   'Never state certainty above "moderate confidence". Avoid words like "guaranteed", "certain", or "sure thing".',
   'hard', true),
  ('guardrail', 'no_position_sizing',
   'Never suggest a specific dollar amount or percentage of a portfolio to allocate to this stock.',
   'hard', true),
  ('guardrail', 'cite_context_only',
   'Base the recommendation only on the provided ML signal, technical indicators, and retrieved news context. Do not invent facts not present in the given context.',
   'soft', true)
on conflict (rule_key) do nothing;
