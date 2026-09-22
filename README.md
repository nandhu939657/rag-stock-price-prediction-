# RAG Stock Advisor

A personal, single-user stock buy/sell/hold advisor. React frontend, Supabase (Postgres +
pgvector) for storage, and a Python FastAPI backend that runs a hybrid RAG + ML pipeline.
Every recommendation closes a loop: live price data feeds a trained XGBoost model for a
quantitative signal; that signal combines with RAG-retrieved live news (Firecrawl +
Apify) *and* RAG-retrieved principles from a curated library of investing/trading books
(see below); Groq's LLM synthesizes all of it under stored guardrail rules into the final
recommendation with real causal reasoning. Tracked stocks refresh automatically every
5 minutes. See [PLAN.md](PLAN.md) for the full design.

**Setting this up fresh (your own Supabase project and API keys)?** Use
[SETUP.md](SETUP.md) instead of this file — it's a from-zero walkthrough written for
that. The rest of this README documents the currently-running reference instance.

## Strategy knowledge base

`backend/scripts/seed_strategy_knowledge.py` seeds `strategy_knowledge` with 31 original
summaries (not verbatim book text) of core principles from 15 well-known investing and
trading books - Graham's *The Intelligent Investor*, O'Neil's CANSLIM, Livermore's
*Reminiscences of a Stock Operator*, Murphy/Pring's technical analysis classics, Douglas's
*Trading in the Zone*, Malkiel's *A Random Walk Down Wall Street*, and more - deliberately
spanning value, growth, momentum, technical, psychology, risk management, and passive
investing philosophies. Each is embedded and retrieved via `match_strategy_knowledge`
(pgvector, see `supabase/migrations/0009_strategy_knowledge.sql`), matched against the
**current technical situation** of the stock being analyzed (e.g. "oversold RSI, price
near lower Bollinger band") rather than injected wholesale into every prompt - so Groq
only sees principles that are actually relevant to what's happening right now, and is
instructed to name the book/author when it genuinely applies one (see
`app/rag/prompt_templates.py`). Browse the full library, and see which principles were
considered for any specific recommendation, on the **Settings** page and the
"Principles considered" chips on any recommendation.

Re-run the seed script any time to change or extend the library - it clears and
reinserts, so editing `STRATEGIES` in that file and re-running is the way to update it.

## Status

The Supabase schema is live (migrations already applied to your project) and the full
backend + frontend codebase is scaffolded, wired together, and all four third-party
integrations (Supabase, Groq, Infoway, Firecrawl, Apify) have been tested live and
confirmed working end-to-end. **Not yet done:** the ML model hasn't been trained yet
(falls back to a heuristic signal until you run `train.py` - see below).

## API keys in use

All configured in a single `.env` file at the **project root** (not inside `backend/`
or `frontend/`) — both the backend and the frontend read from it. The backend reads
every variable directly; the frontend (Vite) only ever reads the `VITE_`-prefixed ones
and automatically excludes everything else from the browser bundle, so the secret keys
below never reach the client even though they live in the same file. See
`frontend/vite.config.ts` (`envDir`) and `backend/app/config.py` (`ROOT_ENV_FILE`).

| Variable | Provider | Used for |
|---|---|---|
| `SUPABASE_*` | Your Supabase project | Storage, RAG corpus, realtime |
| `GROQ_API_KEY` | Groq (`openai/gpt-oss-120b`) | Final recommendation synthesis |
| `MARKET_DATA_API_KEY` | [Infoway](https://infoway.io/) | Real OHLCV price data |
| `FIRECRAWL_API_KEY` | [Firecrawl](https://www.firecrawl.dev/) | News/article scraping for RAG |
| `APIFY_API_TOKEN` | [Apify](https://apify.com/) (`apify/google-search-scraper`) | Additional news scraping |

**Heads up on Infoway:** the key in the root `.env` file is a 7-day free trial key. If price
data suddenly starts failing after working fine before, the trial has likely expired -
renew/upgrade it at https://infoway.io/.

**Markets covered:** US (~14.8k symbols), China A-shares (~5.6k), Hong Kong (~4.2k), India
(~5.6k), and Japan (~3.9k) - all five confirmed working for both symbol search and real
price data. US/China/Hong Kong go through Infoway directly. India and Japan route
through **Yahoo Finance** instead (via the free `yfinance` library, no API key needed -
see `app/ingestion/yahoo_finance_client.py`), since Infoway's price endpoint doesn't
cover those two markets on this plan even though it lists their symbols. It's an
unofficial API, so if it ever breaks or gets rate-limited, analysis for India/Japan
degrades gracefully (news-only) rather than crashing - same as every other data source
in this app.

Search results are transparent about all of this: any symbol without working price data
shows a "No price data" tag before you click it, and suggests a working alternative
listing when one exists (e.g. searching an India-only stock that also has a US ADR).

The app degrades gracefully if any key stops working (heuristic ML signal instead of a
trained one, no news context instead of RAG-backed reasoning) rather than crashing.

## Project structure

```
.env         Single env file for both backend and frontend (not committed)
backend/     FastAPI service: scheduler, ML model, RAG, Groq calls, all third-party API calls
frontend/    React (Vite) SPA
supabase/    SQL migrations + seed data (already applied to your live project)
scripts/     One-off scripts (e.g. run_migrations.py)
PLAN.md      Full architecture/design document
```

## Running the backend

```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend starts an internal scheduler that refreshes every tracked stock every
5 minutes (configurable via `SCHEDULER_INTERVAL_MINUTES` in the root `.env` file).

API docs (Swagger UI) once running: http://localhost:8000/docs

### Training the ML model (optional but recommended)

Without this, the pipeline falls back to a simple RSI/MACD heuristic signal.

```bash
cd backend
./venv/Scripts/python.exe -m app.ml.train
```

This pulls ~2 years of daily bars for a curated basket of ~30 liquid tickers (requires
`MARKET_DATA_API_KEY` to be set), trains an XGBoost direction classifier + return
regressor, and saves artifacts to `backend/app/ml/artifacts/`. Re-run periodically
(e.g. monthly) to refresh the model — it's a manual CLI step, not automated.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at http://localhost:5173. Talks to Supabase directly (read-only, anon key) for
live watchlist/recommendation data, and to the backend (`http://localhost:8000` by
default, see `VITE_API_BASE_URL` in the root `.env` file) for actions that trigger the
pipeline.

## Using the app

1. Go to **Search**, look up or type a ticker, click **Analyze**.
2. Review the recommendation, then **Add to Watchlist** to start auto-tracking it.
3. The **Watchlist** page shows all tracked stocks with live-updating recommendations
   (via Supabase realtime — no manual refresh needed).
4. Click a ticker to see its price chart, indicators, and full recommendation history.
5. **Stop tracking** removes it from the 5-minute refresh cycle.

## Notes / known limitations (v1)

- The ML model is trained on **daily** bars but applied to the **5-minute** bars the
  live pipeline fetches (see `backend/app/ml/train.py` docstring) — a deliberate v1
  simplification; a future improvement is training a proper intraday model once enough
  5-minute history accumulates.
- News scraping is decoupled from the 5-minute price refresh (re-scraped roughly hourly
  per stock, via `NEWS_RESCRAPE_INTERVAL_HOURS`) to conserve Firecrawl/Apify quota.
- The Apify search actor takes roughly 1-3 minutes per real run (it's a live Google
  SERP fetch, not instant). The pipeline polls for it and if it doesn't finish in time,
  that stock's analysis just proceeds without Apify's results rather than failing -
  Firecrawl still contributes news context on its own.
- Guardrails (disclaimer, no leverage advice, no position sizing, confidence cap) are
  enforced via the system prompt and checked post-generation — see
  `backend/app/rag/guardrails.py`. This is a practical safeguard, not a compliance
  guarantee; the UI also shows an independent disclaimer banner.
- Single-user app, no authentication. If you ever deploy this publicly, tighten the
  Supabase RLS grants in `supabase/migrations/0007_rls_policies.sql` first.
