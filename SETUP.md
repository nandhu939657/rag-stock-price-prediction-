Set up and run the "RAG Stock Advisor" project in this folder, end-to-end, on this machine. This is a full-stack app: a Python FastAPI backend (with an ML model, RAG pipeline, and a scheduler) and a React/Vite frontend. Do the setup yourself using your terminal/file tools — don't just tell me the steps, actually run them and fix anything that breaks along the way. Ask me questions only if you get truly stuck; otherwise proceed autonomously.

## Before anything else

1. Confirm a single `.env` file already exists **at the project root** (same folder as this file, `README.md`, `backend/`, and `frontend/`) and is filled in — not just `.env.example`. I already have this — it holds live API keys for Supabase, Groq, Infoway, Firecrawl, and Apify, plus the `VITE_`-prefixed values the frontend needs. Both the backend and the frontend read this same one file (the backend reads it directly; Vite is configured with `envDir: ".."` to read it from the frontend folder too — see `frontend/vite.config.ts`). If it's missing or empty, stop and tell me — don't try to generate placeholder values or sign up for anything yourself.
2. Confirm Python 3.11+ and Node.js 18+ are installed (`python --version` or `python3 --version`, `node --version`). If either is missing, tell me rather than trying to install a system runtime yourself.

## 1. Apply the database schema

The SQL migrations in `supabase/migrations/` (9 files, numbered) need to run against the Supabase project referenced in the root `.env`'s `DATABASE_URL`. They're idempotent (`create table if not exists`, `create or replace function`), so it's safe to run even if some already applied.

From the project root:
```
python -m venv .setup-venv
```
Activate it (`.setup-venv\Scripts\activate` on Windows, `source .setup-venv/bin/activate` on Mac/Linux), then:
```
pip install psycopg2-binary
python scripts/run_migrations.py
```
Confirm it prints `OK` for all 9 migration files plus `seed.sql`, ending with `Done.`. If any migration errors, read the error, fix the root cause if it's something reasonable (e.g. a transient connection issue — retry), and re-run. If it's a real schema conflict, stop and tell me.

## 2. Set up and start the backend

```
cd backend
python -m venv venv
```
Activate it (`venv\Scripts\activate` on Windows, `source venv/bin/activate` on Mac/Linux), then:
```
pip install -r requirements.txt
```
This pulls in ML/embedding libraries (torch, sentence-transformers, xgboost) and can take a few minutes and a few hundred MB — that's expected, not a hang.

Seed the strategy-knowledge library (book-derived investing principles used by the RAG pipeline — also idempotent, safe to re-run):
```
python scripts/seed_strategy_knowledge.py
```

Start the backend in the background (or a dedicated terminal/tab) so it keeps running:
```
uvicorn app.main:app --reload --port 8000
```
Verify it's actually up by curling `http://localhost:8000/api/health` and confirming it returns `{"status":"ok", ...}`. If it fails, read the traceback — likely causes are a missing value in the root `.env` or a dependency install issue — fix and retry before moving on. (The backend resolves the root `.env` by absolute path — see `ROOT_ENV_FILE` in `backend/app/config.py` — so it works regardless of the directory you launch `uvicorn` from.)

## 3. Set up and start the frontend

In a separate terminal/process (don't kill the backend):
```
cd frontend
npm install
npm run dev
```
Verify it's serving by checking `http://localhost:5173` returns HTTP 200. If the app complains about missing `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` in the browser console, check the root `.env` has those two keys set (not just the backend's `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`, which are different values for a different purpose).

## 4. Confirm it actually works

Hit `http://localhost:8000/api/stocks/search?q=AAPL` and confirm it returns real symbol results (not an error) — this proves the Infoway/market-data key in `.env` is valid, not just that the server booted.

## 5. Report back

Tell me:
- Whether both servers are running and healthy (backend on :8000, frontend on :5173).
- The exact commands you used to start each, so I know how to restart them later.
- Any step that failed and how you resolved it (or couldn't).

## Optional: train the ML model

The app works without this (falls back to a simpler RSI/MACD heuristic). If I ask for it:
```
cd backend
python -m app.ml.train
```
This trains on live market data and takes a few minutes — only run it if I explicitly ask.

## Guardrails for you while doing this

- Never print, log, or otherwise expose the contents of the root `.env` file back to me in chat — it contains private API keys, including ones (Supabase service_role, Groq, Infoway, Firecrawl, Apify) that must never end up in frontend code or a browser-visible response. Redact them if you need to reference a value while debugging.
- Only the `VITE_`-prefixed variables in `.env` are meant to reach the browser (Vite enforces this automatically) — if you ever see a non-`VITE_` secret show up in frontend build output or browser devtools, treat that as a real bug and tell me immediately rather than shipping it.
- Don't commit anything to git, don't modify application source code to "fix" a setup problem unless the problem is clearly a bug in the code itself (e.g. a typo causing a crash) rather than an environment issue.
- If a step needs a 7-day-trial API key (Infoway) that looks expired (auth errors that previously worked), tell me instead of trying to work around it.
