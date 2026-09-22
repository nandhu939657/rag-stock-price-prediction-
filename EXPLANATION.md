# How This Project Works

A complete explanation of the RAG Stock Advisor — what it does, the tech stack, the ML
model, how RAG (Retrieval-Augmented Generation) actually helps, every external API in
use, and the full pipeline from a button click to a recommendation on screen.

---

## 1. What the app actually does

It's a personal stock research tool. You search for a company, and it gives you a
**buy / sell / hold** recommendation with a written explanation — not a canned template,
but reasoning grounded in four real inputs: live price data, a trained machine learning
signal, live news, and a curated library of investing-book principles. You can add a
stock to a watchlist, and it re-analyzes itself automatically every 5 minutes, so the
recommendation and its reasoning update on their own as the market moves and news comes
in.

It covers five markets: **US, China, Hong Kong, India, and Japan** — roughly 33,000
tradable symbols in total.

---

## 2. Tech stack

**Frontend** — React 18 + TypeScript, built with Vite.
- `react-router-dom` for page navigation (Dashboard, Overview, Search, Stock Detail, Settings)
- `recharts` for every chart (price chart, sparklines, the buy/sell/hold donut, the movers bar chart)
- `lucide-react` for icons
- `@supabase/supabase-js` for direct, read-only database access and live updates
- Plain CSS with a small design-token system (no Tailwind/component library) — supports light and dark mode

**Backend** — Python, FastAPI.
- `uvicorn` runs the server
- `APScheduler` runs the 5-minute background refresh loop
- `pandas` / `numpy` for indicator math and feature engineering
- `xgboost` for the ML model
- `sentence-transformers` for turning text into vectors (runs locally, no API)
- `groq` (official SDK) for the LLM call
- `httpx` for all outbound HTTP (market data, Firecrawl, Apify)
- `supabase-py` for database reads/writes from the backend
- `yfinance` as a free fallback price-data source

**Database** — Supabase, which is a hosted Postgres database plus extras. Two things
about it matter here:
- **pgvector**, a Postgres extension that lets the database store AI embeddings (long
  lists of numbers representing meaning) and search them by similarity — this is what
  makes RAG possible without a separate vector database.
- **Realtime**, which lets the frontend watch specific tables and get pushed updates the
  instant a row changes — that's how the watchlist updates live without polling.

---

## 3. Every external API/service and what it's for

| Service | What it does here | Free? |
|---|---|---|
| **Supabase** | The database itself — stores everything | Yes (free tier) |
| **Groq** | Runs the LLM (`openai/gpt-oss-120b`) that writes the final recommendation | Yes (free tier) |
| **Infoway** | Real price/candle data for US, China, and Hong Kong stocks | 7-day trial |
| **Yahoo Finance** (via the `yfinance` library) | Real price data for India and Japan — Infoway doesn't cover those two markets on the trial plan, so this fills the gap. No signup, no key. | Yes, free, no key |
| **Firecrawl** | Scrapes and returns clean article text for a stock's recent news | Yes (free tier) |
| **Apify** | Runs a Google Search scrape as a second, independent news source | Free trial credits |

Two market-data providers exist because Infoway (the primary one) simply doesn't have
working price data for India and Japan on its current plan, even though it lists their
company names. Rather than leave those markets broken, the app quietly routes those two
markets to Yahoo Finance instead — same interface, different source underneath.

Two news providers (Firecrawl and Apify) exist for redundancy: they run **concurrently**,
and if one fails or times out, the other's results still make it into the analysis.

---

## 4. The ML model

**What it is:** an XGBoost model — specifically two of them, a *classifier* that predicts
direction (`up`, `down`, or `flat`) and a *regressor* that predicts the size of the move.
XGBoost is a fast, well-tested "gradient boosted trees" algorithm — a common, practical
choice for this kind of structured, tabular prediction (much lighter to train and run
than a deep learning model, and it works well with a modest amount of data).

**What it looks at (the features):**
- Price returns over the last 1, 5, 10, and 20 periods
- Price position relative to its 20-period moving averages (SMA and EMA)
- RSI(14) — a classic overbought/oversold indicator
- MACD and its signal/histogram — a momentum indicator
- Where the price sits within its Bollinger Bands (0 = at the lower band, 1 = at the upper band)
- Rolling volatility over the last 20 periods
- Current trading volume relative to its recent average

**How it's trained:** offline, as a one-time (or periodic) script — not live during a
request. It pulls about two years of daily price history across a curated basket of
roughly 30 large, liquid, well-known US stocks (Apple, Microsoft, Amazon, and similar),
builds the features above for every day, and trains on that combined dataset. Training
across many stocks at once — rather than one model per stock — means a brand-new,
just-searched company still gets a usable signal immediately, instead of needing months
of its own history first.

**The cold-start fallback:** if the model hasn't been trained yet, or a stock doesn't
have enough price history yet for the features to make sense, the app falls back to a
simple, transparent rule: oversold RSI or a positive MACD histogram nudges toward "up,"
overbought RSI or negative MACD nudges toward "down." This fallback is always clearly
labeled as a heuristic (not the trained model) wherever it's used, including inside the
prompt sent to the LLM, so the AI knows to treat it as lower-confidence.

**What it hands off:** a signal (`up`/`down`/`flat`), a predicted return, and a
confidence score. It does **not** make the final call — it's one input the LLM weighs
alongside news and strategy knowledge.

---

## 5. How RAG helps — and there are actually two separate RAG systems here

RAG stands for **Retrieval-Augmented Generation**: instead of asking an LLM to answer
from memory alone, you first *retrieve* the most relevant real information from a
database, then hand that to the LLM as context so its answer is grounded in something
real rather than made up. This app uses RAG twice, for two different kinds of knowledge.

### 5a. News RAG — "what's actually happening with this company right now"

1. Firecrawl and Apify scrape recent news/articles about the company (run at the same
   time, not one after another, to keep things fast).
2. Long articles get split into smaller chunks (~400 words each, with a little overlap
   so no sentence gets cut off mid-thought and lose context).
3. Each chunk is converted into a 384-number vector (an "embedding") using a small,
   local AI model (`all-MiniLM-L6-v2`) that runs entirely on the backend — no external
   API call, no per-use cost.
4. Those vectors get stored in Postgres via pgvector, tagged to that specific stock.
5. When it's time to analyze the stock, the app embeds a short query like *"Apple Inc
   AAPL recent news and outlook"* and asks Postgres for the 5 stored chunks whose
   vectors are mathematically closest to that query's vector — meaning, whichever
   chunks are actually *about* that topic, regardless of exact keyword matches.
6. Those 5 chunks get handed to the LLM as real, dated, sourced news context.

This is why the app can talk about a specific company's actual recent headlines instead
of generic, dated knowledge from whenever the LLM was trained.

### 5b. Strategy RAG — "which investing wisdom actually applies to this situation"

This is the newer, more unusual piece. The app has a library of **31 original summaries
of core principles from 15 well-known investing and trading books** — value investing
(Graham's *The Intelligent Investor*), growth investing (O'Neil's CANSLIM system,
Lynch's *One Up On Wall Street*), technical analysis (Murphy and Pring's classics),
trend-following and trading psychology (Livermore's *Reminiscences of a Stock Operator*,
Douglas's *Trading in the Zone*), risk management (Van Tharp, Minervini), momentum
factor investing (*Quantitative Momentum*), and passive/efficient-market thinking
(Malkiel, Bogle) — deliberately spanning very different, sometimes opposing,
philosophies.

Each principle is embedded the same way as news chunks and stored in its own table. But
here's the key difference: **the retrieval query isn't about the company — it's about
the current technical situation.** The app builds a plain-language description like
*"oversold RSI at 28, bearish MACD momentum, price near the lower Bollinger band"* and
retrieves whichever book principles are most relevant to *that state*, regardless of
which company it is. That means the same "cut your losses fast" principle from
O'Neil can surface for any stock in a similar losing position, and a bounce-focused
principle can surface for any stock that looks technically oversold — the retrieval is
about the pattern, not the ticker.

The LLM is explicitly instructed to only use a retrieved principle if it genuinely
applies to this specific case (and to name the book when it does), rather than reciting
all of them as a checklist. In testing, this produces genuinely different reasoning —
for one real analysis, the model wrote *"Trend-following ideas advise following the
current direction but respecting resistance, and Quantitative Momentum cautions that
momentum can reverse sharply"* — that's the retrieved knowledge actually shaping the
conclusion, not just decorating it.

**Why not just paste every rule into every prompt?** Two reasons: it would bloat every
single request with mostly irrelevant material (most of the 31 principles don't apply to
any given moment), and it would make the LLM's job harder, not easier — the model
would spend effort figuring out what to ignore. Retrieving only what's relevant keeps
the context tight and focused.

---

## 6. How the final recommendation actually gets written

Once the ML signal, the retrieved news, and the retrieved strategy principles are all
ready, they get combined into one call to Groq's LLM (`openai/gpt-oss-120b`, a
"reasoning" model — it thinks through a hidden chain of reasoning before producing its
final answer, similar in spirit to how a person might reason for a moment before
speaking).

**The system prompt** (fixed instructions for every single call) does two jobs:
1. Injects the **guardrails** — five rules stored in the database (always disclose this
   isn't financial advice, never recommend leverage, never suggest position sizes, cap
   how certain the language can sound, and only use the provided context — don't invent
   facts). Because these live in the system prompt, separate from the news/data content,
   it's harder for something odd embedded in a scraped article to override them.
2. Requires **genuine causal reasoning**, not a restatement of numbers. Early on, the
   model would write things like "RSI is oversold, so limited upside" — which is
   backwards (oversold usually signals a bounce is more likely, not less). The prompt
   now explicitly teaches the model the standard, correct meaning of each indicator, and
   requires it to build reasoning as a chain: what the technicals imply → what the ML
   signal adds → what the news adds → which strategy principles genuinely apply → the
   actual call and why it follows from all of that.

**The user message** (built fresh for every request) contains: the ticker, the ML
signal and confidence, the current indicator values, the 5 retrieved news chunks, and
the retrieved strategy principles.

**The response** is required to come back as strict JSON — `{"recommendation":
"buy"|"sell"|"hold", "reasoning": "..."}` — which is then checked automatically: does it
contain the disclaimer, does it avoid banned overconfident language? If it fails that
check, the app asks the model to revise once; if it still fails, the disclaimer gets
appended programmatically as a last resort, so a compliant result is guaranteed either
way.

---

## 7. The full pipeline, step by step

This exact sequence runs both when you click "Analyze" and, automatically, every 5
minutes for anything on your watchlist — it's the same code path either way, so the two
never drift apart.

1. **Resolve the stock** — look it up or create a new row for it.
2. **Fetch price data** — from Infoway (US/China/Hong Kong) or Yahoo Finance
   (India/Japan), then compute all the technical indicators and store the new bars.
3. **Run the ML model** — build the feature vector from the latest price data, get a
   signal, predicted return, and confidence (or fall back to the heuristic if there's
   not enough history yet).
4. **Scrape news, if stale** — only re-scrape if the stored news for this stock is
   older than about an hour, to avoid hammering Firecrawl/Apify on every 5-minute tick.
   Firecrawl and Apify run at the same time; whichever finishes contributes, and a slow
   or failed one doesn't block the other.
5. **Retrieve relevant news** (RAG #1) — pgvector similarity search scoped to this stock.
6. **Retrieve relevant strategy knowledge** (RAG #2) — pgvector similarity search
   against the current technical situation, not the company.
7. **Ask Groq for the recommendation** — with guardrails, the ML signal, the news, and
   the strategy principles all in the prompt.
8. **Validate the guardrails** on the response; fix up if needed.
9. **Store the result** — a full audit-trail row: the recommendation, the reasoning,
   which guardrails were checked, which news chunks and strategy principles were used,
   and a snapshot of the indicators at that moment.
10. **Return it** — the frontend shows it immediately (on-demand), or it just appears
    live on the watchlist a moment later (scheduled), via Supabase's realtime push.

---

## 8. What happens when something's missing or wrong

The app is built to degrade gracefully rather than break:
- **No price data found for a symbol** (wrong ticker, delisted, or a market this app
  doesn't cover) → the LLM is explicitly told not to invent technical details, and says
  so plainly in the reasoning. The UI also shows a visible warning banner, and the
  search results flag any symbol without real price data *before* you click it —
  sometimes suggesting a working alternative listing for the same company.
- **News scraping fails or times out** → the analysis still proceeds on whatever's
  already stored, or with no news context at all — it just doesn't crash.
- **The ML model isn't trained yet** → falls back to the labeled heuristic.
- **A market data or news API key is missing** → that one piece degrades; the rest of
  the pipeline still runs.

---

## 9. The database (Supabase / Postgres) — what's actually stored

- **`stocks`** — every company ever looked up.
- **`tracked_stocks`** — the watchlist (which stocks auto-refresh, and when they last did).
- **`price_history`** — OHLCV bars plus every computed indicator, one row per bar per stock.
- **`knowledge_base`** — the 5 guardrail rules injected into every LLM call.
- **`document_chunks`** — the embedded news RAG corpus, tagged per stock.
- **`strategy_knowledge`** — the embedded book-principle RAG corpus (31 rows, 15 books).
- **`recommendations`** — the full history of every call ever made, with reasoning and
  full context, so nothing is a black box after the fact.

Two Postgres functions (`match_document_chunks`, `match_strategy_knowledge`) do the
actual vector similarity search, so that math happens inside the database rather than
pulling every row into Python first.

---

## 10. What's on each page (frontend)

- **Dashboard** — your watchlist: buy/sell/hold counts, a donut chart of the split,
  per-stock confidence gauges and price sparklines, sort/filter controls, and a manual
  "refresh now" button per stock.
- **Overview** — top gainers and top losers, as both a bar chart and a ranked list,
  scoped honestly to stocks this app has actually analyzed (not a full market scan).
- **Search** — live autocomplete across all five markets as you type, with "no price
  data" warnings and suggested alternatives built in, then a full recommendation with
  price chart and indicators once you analyze something.
- **Stock Detail** — tabbed: Overview (chart + indicators + latest call), News & Sources
  (the actual retrieved articles, with links out), and History (every past call).
- **Settings** — live system health, the 5 active guardrails, and the full strategy
  library (all 15 books and their principles, browsable) — full transparency into
  what's shaping every recommendation.

---

## 11. Honest limitations

- **Single-user, no login.** Not built for multiple accounts.
- **The ML model trains on daily bars but is applied to 5-minute bars** during live
  tracking — a deliberate simplification to ship something useful without needing
  months of intraday history for every stock; a future improvement would train a
  proper intraday model.
- **Yahoo Finance (India/Japan) is an unofficial API** — it works today, confirmed
  live, but isn't a guaranteed contract the way Infoway's official API is.
- **Apify's news search can take 1-3 minutes** on a slow run; the app caps how long it
  waits and just proceeds without it if it's too slow, rather than making you wait.
- **This is not financial advice** — enforced as an actual guardrail, not just a
  disclaimer of convenience, and shown independently in the UI regardless of what any
  individual AI response says.
