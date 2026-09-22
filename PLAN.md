# RAG + ML Stock Buy/Sell/Hold Advisor — Implementation Plan

## Context

The user wants a personal stock advisor app: search a stock, get an AI-driven buy/sell/hold recommendation, and track a watchlist that automatically refreshes its recommendation every 5 minutes. The core idea is a **hybrid RAG + ML pipeline**: a trained ML model reads price/technical-indicator data to produce a quantitative signal, and a Groq-hosted LLM combines that signal with retrieved news/sentiment context (via RAG over Supabase/pgvector) and stored "guardrail" rules to produce the final recommendation with reasoning. Firecrawl and Apify supply the raw news/text that feeds the RAG knowledge base; a dedicated market-data API supplies the actual price ticks (Firecrawl/Apify can't reliably provide real-time OHLC data). The project is greenfield — the working directory started empty.

Decisions already confirmed with the user (via clarifying questions):
- **Price data**: a dedicated market-data API (not scraped), separate from Firecrawl/Apify which are used only for news/sentiment text.
- **Prediction engine**: hybrid — ML model produces a quantitative signal, Groq LLM synthesizes the final recommendation from that signal + RAG context + guardrails.
- **Backend**: a separate Python (FastAPI) backend service owns the scheduler, ML model, and all third-party API calls (Firecrawl, Apify, Groq, market data) — a browser-only React app can't run a reliable 5-minute background scheduler.
- **Auth**: none — single-user app, no login/signup.

Intended outcome: a working full-stack app (React frontend + Supabase DB + Python backend) that lets the user analyze any stock on demand, add/remove stocks from a tracked watchlist, and see recommendations that auto-refresh every 5 minutes for tracked stocks, each with a natural-language explanation and a visible history/track record.

---

## 1. Repo / Folder Structure

Monorepo with two sibling apps plus versioned Supabase migrations (simplest for a single-developer project; deploy frontend to Vercel/Netlify, backend to Railway/Render/Fly.io):

```
rag-stock-price-prediction/
├── frontend/                          # React SPA (Vite + TypeScript)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SearchAnalyzePage.tsx
│   │   │   ├── WatchlistDashboardPage.tsx
│   │   │   ├── StockDetailPage.tsx
│   │   ├── components/
│   │   │   ├── RecommendationCard.tsx
│   │   │   ├── PriceChart.tsx
│   │   │   ├── IndicatorPanel.tsx
│   │   │   ├── ReasoningPanel.tsx
│   │   │   ├── HistoryTable.tsx
│   │   │   ├── AddToWatchlistButton.tsx
│   │   │   ├── TrackedStockCard.tsx
│   │   ├── lib/
│   │   │   ├── supabaseClient.ts      # supabase-js init (anon key, read-only)
│   │   │   ├── apiClient.ts           # fetch wrapper for FastAPI backend
│   │   │   ├── realtime.ts            # realtime subscription hooks
│   │   ├── hooks/
│   │   │   ├── useTrackedStocks.ts
│   │   │   ├── useRecommendationHistory.ts
│   │   │   ├── useLiveRecommendation.ts
│   │   ├── types/db.ts                # generated Supabase types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.local                     # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
│   └── package.json
│
├── backend/                           # Python FastAPI service
│   ├── app/
│   │   ├── main.py                    # FastAPI app, routers, scheduler startup
│   │   ├── config.py                  # pydantic Settings, loads .env
│   │   ├── api/
│   │   │   ├── routes_stocks.py       # search/analyze, add/remove tracking
│   │   │   ├── routes_recommendations.py
│   │   │   ├── routes_history.py
│   │   ├── scheduler/refresh_job.py   # APScheduler, 5-min loop over tracked stocks
│   │   ├── ingestion/
│   │   │   ├── market_data_client.py  # OHLC + indicators source
│   │   │   ├── indicators.py          # SMA/EMA/RSI/MACD/Bollinger/volatility
│   │   │   ├── firecrawl_client.py
│   │   │   ├── apify_client.py
│   │   │   ├── chunker.py
│   │   │   ├── embeddings.py          # local sentence-transformers model
│   │   ├── ml/
│   │   │   ├── features.py
│   │   │   ├── train.py               # offline training CLI script
│   │   │   ├── model.py               # load + predict wrapper
│   │   │   ├── artifacts/             # saved model files (gitignored)
│   │   ├── rag/
│   │   │   ├── retriever.py           # pgvector similarity search
│   │   │   ├── guardrails.py          # prompt assembly + post-validation
│   │   │   ├── prompt_templates.py
│   │   ├── llm/groq_client.py
│   │   ├── pipeline/analyze_stock.py  # shared orchestration (on-demand + scheduled)
│   │   ├── db/supabase_client.py      # service_role key client
│   │   └── models_schemas.py
│   ├── requirements.txt
│   └── .env                           # FIRECRAWL_API_KEY, APIFY_API_TOKEN, GROQ_API_KEY, MARKET_DATA_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
│
├── supabase/
│   ├── migrations/
│   │   ├── 0001_enable_pgvector.sql
│   │   ├── 0002_stocks_and_tracking.sql
│   │   ├── 0003_price_history.sql
│   │   ├── 0004_knowledge_base_guardrails.sql
│   │   ├── 0005_document_chunks.sql
│   │   ├── 0006_recommendations.sql
│   │   └── 0007_rls_policies.sql
│   └── seed.sql                       # initial guardrail rows, sample stocks
│
├── .gitignore
└── README.md
```

---

## 2. Supabase Schema

Enable pgvector first: `create extension if not exists vector;`

- **`stocks`** — master list: `id uuid pk`, `ticker text unique`, `name`, `exchange`, `sector`, `created_at`.
- **`tracked_stocks`** — watchlist state: `id`, `stock_id fk`, `is_tracked bool`, `added_at`, `removed_at`, `last_refreshed_at`, `unique(stock_id)`.
- **`price_history`** — OHLCV + indicators, one row per stock per interval: `stock_id fk`, `ts`, `open/high/low/close/volume`, `sma_20`, `ema_20`, `rsi_14`, `macd/macd_signal/macd_hist`, `bollinger_upper/lower/mid`, `volatility_20`, `unique(stock_id, ts)`, indexed on `(stock_id, ts desc)`.
- **`knowledge_base`** — guardrails + domain facts (structured rules, not embedded): `category` (`guardrail`|`domain_fact`), `rule_key`, `content` (injected verbatim into system prompt), `severity` (`hard`|`soft`), `is_active`. Seed rows: mandatory disclaimer, no-leverage-recommendation, confidence-cap (no "guaranteed"/"certain" language), no specific position-sizing advice.
- **`document_chunks`** — RAG corpus (scraped news, embedded): `stock_id fk` (nullable for general market news), `source` (`firecrawl`|`apify`), `source_url`, `title`, `published_at`, `chunk_text`, `chunk_index`, `embedding vector(384)`, `scraped_at`. Index: `ivfflat (embedding vector_cosine_ops)` (or `hnsw` if available) plus `(stock_id, scraped_at desc)`.
- **`recommendations`** — prediction/decision audit trail: `stock_id fk`, `created_at`, `ml_signal` (`up`|`down`|`flat`), `ml_predicted_return`, `ml_confidence`, `final_recommendation` (`buy`|`sell`|`hold`), `reasoning text`, `guardrails_applied text[]`, `context_snapshot jsonb` (indicators + chunk ids + ml output, for reproducibility), `triggered_by` (`scheduled`|`on_demand`). Indexed on `(stock_id, created_at desc)`.

**RLS**: single-user local app — simplest is RLS disabled, frontend uses the Supabase **anon key with select-only grants**, backend uses the **service_role key** for all writes. Never ship the service_role key into the frontend bundle. If ever deployed publicly, tighten anon grants further.

---

## 3. End-to-End Pipeline

Both flows below call one shared orchestration function, `pipeline/analyze_stock.py`, with a `mode`/`triggered_by` flag — avoids duplicating pipeline logic between on-demand and scheduled runs.

### (a) On-demand "Analyze this stock"
1. Frontend → `POST /api/stocks/analyze { ticker }`.
2. Backend upserts into `stocks` (symbol lookup via market-data API if new).
3. Fetch recent OHLCV from the market-data API → compute indicators → upsert `price_history`.
4. Scrape news via Firecrawl + Apify **only if no fresh chunks exist within the last few hours** (avoid redundant scraping cost) → chunk (~500 tokens, ~50 overlap, sentence-boundary aware) → embed locally → insert into `document_chunks`.
5. ML inference: build feature vector from latest `price_history`, predict direction + confidence. If insufficient history (cold start), fall back to a simple indicator-threshold heuristic and mark confidence low.
6. RAG retrieval: embed a query built from ticker + "recent news and outlook", run pgvector cosine similarity search scoped to `stock_id`, top-k ~5 chunks.
7. Guardrails: pull active `knowledge_base` guardrail rows, assemble into the system prompt.
8. Groq call: system prompt (guardrails) + user message (ML signal, indicators, retrieved chunks) → request structured JSON output `{ recommendation, reasoning }`.
9. Post-validation: check disclaimer present, banned-phrase absence; re-prompt once on failure, else programmatically append disclaimer and flag it.
10. Insert into `recommendations` (`triggered_by='on_demand'`, full `context_snapshot`).
11. Return recommendation to frontend (backend already wrote to Supabase via service key).

### (b) Recurring 5-minute tracked-stock refresh
1. APScheduler fires every 5 minutes; query `tracked_stocks` where `is_tracked = true`.
2. For each tracked stock, run the same `analyze_stock.py` orchestration (`triggered_by='scheduled'`):
   - Fetch only new bars since `last_refreshed_at` (incremental, not full history).
   - Re-scrape news only if the last scrape is older than a configurable threshold (e.g. 1 hour) — decouple scraping cadence from price cadence to conserve Firecrawl/Apify quota.
   - Recompute indicators, ML inference, RAG retrieval, Groq synthesis, insert new `recommendations` row, update `last_refreshed_at`.
3. Frontend watchlist subscribes via `supabase-js` realtime channel on `recommendations`/`tracked_stocks`, so new results appear live with no polling from the frontend.

---

## 4. ML Model

- **Model**: start with **XGBoost** (classifier for direction `up`/`down`/`flat` with a small dead-zone threshold, e.g. ±0.2%, plus predicted-return magnitude). Chosen over LSTM/Prophet for v1: trains fast on tabular features, needs far less data, no GPU, simple to serve in FastAPI via native JSON model format.
- **Features** (from `price_history`): lagged returns (1/5/10/20 periods), SMA/EMA and price-relative-to-SMA ratio, RSI(14), MACD/signal/histogram, Bollinger band position, rolling volatility, volume relative to rolling average, cyclical time-of-day/day-of-week if intraday.
- **Target**: next-interval forward return, discretized for the classifier, raw for the regressor.
- **Training** (`ml/train.py`, offline CLI, not in the live request path): pull 1–2 years of historical OHLCV from the market-data API's bulk historical endpoint (separate budget from live polling) across a **curated basket of ~50–100 liquid tickers** (not one model per ticker) — this avoids needing months of history for every newly tracked stock. Time-based train/validation split (no shuffling, avoid lookahead leakage). Save artifact + a `feature_columns.json` manifest.
- **Serving**: `ml/model.py` loads the artifact once at FastAPI startup (singleton), exposes `predict(stock_id) -> {signal, predicted_return, confidence}`.
- **Retraining**: manual/periodic (e.g. monthly) for v1 — not automated; flag as a later improvement.

---

## 5. RAG Retrieval

- **Chunking**: ~500-token chunks, ~50-token overlap, sentence-boundary aware.
- **Embeddings**: Groq doesn't serve an embeddings endpoint, so run a **local `sentence-transformers/all-MiniLM-L6-v2`** model in the Python backend (384 dims, fast on CPU, no external cost/rate limit) — matches the `vector(384)` column. Loaded once at startup.
- **Similarity search**: expose a Postgres function `match_document_chunks(query_embedding, target_stock_id, match_count)` using `embedding <=> query_embedding` cosine distance, called via `supabase.rpc(...)` from the backend so vector math stays in the DB. Optionally recency-weight/filter (e.g. only chunks from the last 7 days) since news relevance decays fast.

---

## 6. Guardrails Mechanism

- Stored as rows in `knowledge_base` (`category='guardrail'`), each with `rule_key`, `content`, `severity`.
- **Prompt-level enforcement**: every Groq call's **system prompt** includes all active guardrail rules as a bulleted "MUST follow" list (e.g. always disclose "not financial advice", never suggest position sizes/dollar amounts, never recommend leverage/margin/options, avoid certainty language). Guardrails live in the system prompt, separate from the data/context message, to reduce prompt-injection risk from scraped article text.
- **Post-generation validation** (defense in depth): regex/keyword checks for disclaimer presence and banned-phrase absence. On failure: one corrective re-prompt, then a programmatic fallback (append disclaimer, log which rule triggered, record in `guardrails_applied`).
- This is a practical two-layer pattern, not a compliance guarantee — flagged explicitly as such, with a persistent disclaimer banner also rendered independently in the UI (not solely relying on LLM output).

---

## 7. FastAPI Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/stocks/analyze` | One-off analyze a ticker, runs full pipeline |
| POST | `/api/stocks/{ticker}/track` | Add to watchlist, triggers immediate first analysis |
| DELETE | `/api/stocks/{ticker}/track` | Remove from watchlist |
| GET | `/api/stocks/tracked` | Tracked stocks + latest recommendation each |
| GET | `/api/stocks/{ticker}/history` | Paginated recommendation + price history |
| GET | `/api/stocks/search?q=` | Symbol search (proxies market-data API so its key stays server-side) |
| GET | `/api/health` | Scheduler status, last run time |

Frontend reads `tracked_stocks`/`recommendations`/`price_history` directly via `supabase-js` (anon key, realtime subscriptions); it only calls the backend for actions that trigger the pipeline (analyze/track/untrack) or need a protected key (symbol search).

---

## 8. React Frontend

- **`SearchAnalyzePage`**: search input → `/api/stocks/search` → `/api/stocks/analyze` → `RecommendationCard` + `ReasoningPanel` + `IndicatorPanel`, with "Add to Watchlist" button.
- **`WatchlistDashboardPage`**: grid of `TrackedStockCard`s (ticker, color-coded buy/sell/hold badge, confidence, last-updated), live via realtime hooks, click-through to detail, remove button.
- **`StockDetailPage`**: `PriceChart` (OHLC + SMA/EMA/Bollinger overlays), `IndicatorPanel`, `ReasoningPanel` (latest explanation + disclaimer), `HistoryTable` (recommendation track record over time), track/untrack toggle.
- **Shared hooks** (`useTrackedStocks`, `useRecommendationHistory`, `useLiveRecommendation`) centralize `supabase-js` reads + realtime subscriptions.
- **`apiClient.ts`** centralizes backend calls with consistent loading/error handling (graceful degradation on scrape/LLM failures, not a blank screen).

---

## 9. Phased Build Order

1. **Foundations** — Supabase schema + migrations, FastAPI skeleton with stub track/untrack/tracked endpoints (no pipeline yet), React Watchlist page doing add/remove end-to-end. Proves the wiring works.
2. **Market data + indicators** — market-data API client, `indicators.py`, populate `price_history`, real `PriceChart`/`IndicatorPanel`.
3. **RAG ingestion** — Firecrawl/Apify clients, chunking, local embeddings, `document_chunks`, `match_document_chunks` RPC; manually verify retrieval quality (no LLM yet).
4. **ML model** — `train.py` offline training on the curated ticker basket, `model.py` serving, raw ML signal surfaced in UI (independently testable before LLM synthesis exists).
5. **Groq synthesis + guardrails** — seed `knowledge_base`, prompt assembly, Groq call, post-validation, `ReasoningPanel` becomes real. This is where `/api/stocks/analyze` becomes fully live.
6. **Scheduler + realtime** — APScheduler 5-minute job reusing the shared pipeline, incremental fetch via `last_refreshed_at`, Supabase realtime wired into dashboard/detail pages.
7. **Polish** — history timeline, chart polish, error/loading states, rate-limit backoff/queueing, cold-start UI messaging, README + env docs.

---

## 10. Key Risks

- **Market-data rate limits vs 5-min polling**: recommend **Twelve Data** as primary (verify current free-tier limits at signup) or **Finnhub** (60 calls/min free tier) as an alternative; **Alpha Vantage**'s free tier is now very restrictive (≈25 req/day) and likely too tight for multi-stock 5-min polling. Design `market_data_client.py` with rate-limit-aware sequential calls + backoff, and document a practical watchlist-size cap.
- **Firecrawl/Apify cost & ToS**: decouple scraping cadence from the 5-min price cadence (re-scrape per stock every 1–4 hours, not every tick); prefer sources designed for aggregation over scraping paywalled/disallowed sites; degrade gracefully (use stale chunks) if a scrape fails rather than failing the whole pipeline.
- **Not real financial advice**: guardrail-enforced disclaimer in every LLM response, **plus** an independent persistent disclaimer banner in the UI itself.
- **Cold start for newly tracked stocks**: broad-basket-trained model reduces but doesn't eliminate this; define an explicit low-confidence fallback (heuristic signal + UI messaging like "Building history — confidence improves over the next few refreshes") when fewer than ~20 price bars exist.
- **Key security**: Firecrawl, Apify, Groq, market-data, and Supabase `service_role` keys live in a single root `.env` file, but are never `VITE_`-prefixed, so Vite automatically excludes them from the frontend bundle - only the explicitly `VITE_`-prefixed values (anon key, API base URL) reach the browser. (v1 originally split this into `backend/.env` + `frontend/.env.local`; consolidated to one root file later - see SETUP.md.)
- **LLM structured-output reliability**: request Groq JSON-mode output where supported; wrap parsing in try/except with a regex-extract fallback so malformed output doesn't crash the pipeline (default to `hold` + flagged note on total parse failure).

---

## Verification

- **Phase 1**: run FastAPI (`uvicorn app.main:app --reload`) and React (`npm run dev`) locally, add/remove a stock via the UI, confirm rows appear/update in the Supabase table editor.
- **Phase 2**: confirm `price_history` populates with plausible OHLCV + indicator values for a known ticker (e.g. AAPL) and the chart renders correctly.
- **Phase 3**: manually inspect `document_chunks` rows and call `match_document_chunks` via the Supabase SQL editor or a quick backend script to confirm retrieved chunks are topically relevant to the ticker.
- **Phase 4**: run `train.py`, check validation accuracy/MAE printed to console is above a naive baseline (e.g. better than always predicting "flat"), confirm `model.py.predict()` returns sane output for a sample stock.
- **Phase 5**: call `POST /api/stocks/analyze` for a real ticker, confirm the response includes a disclaimer, a buy/sell/hold value, and reasoning that references the actual retrieved news/indicators (not generic boilerplate).
- **Phase 6**: track a stock, wait for two scheduler cycles (~10 min), confirm two new `recommendations` rows appear and the dashboard updates live without a manual page refresh.
- **End-to-end**: search a stock never seen before, analyze it, track it, watch it refresh automatically, then remove it and confirm it stops refreshing and disappears from the dashboard.
