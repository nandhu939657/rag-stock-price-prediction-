"""Core pipeline orchestration - the single function used by BOTH the on-demand
/api/stocks/analyze endpoint and the recurring 5-minute scheduler job, so the two
flows never drift out of sync. See PLAN.md section 3 for the full step-by-step design.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd

from app.config import get_settings
from app.db.supabase_client import get_supabase
from app.ingestion import apify_client, firecrawl_client
from app.ingestion.chunker import chunk_text
from app.ingestion.embeddings import embed_texts
from app.ingestion.indicators import compute_indicators
from app.ingestion.market_data_client import MarketDataUnconfigured, fetch_recent_bars
from app.llm.groq_client import generate_recommendation
from app.ml.features import build_feature_frame, latest_feature_vector
from app.ml.model import get_model_service
from app.rag.guardrails import apply_fallback, assemble_system_prompt, validate_output
from app.rag.prompt_templates import build_user_message
from app.rag.retriever import retrieve_relevant_chunks, retrieve_relevant_strategies

logger = logging.getLogger(__name__)

TriggeredBy = Literal["on_demand", "scheduled"]


def _safe_iso_date(value) -> str | None:
    """Scraped 'published' dates come in all sorts of non-ISO formats (e.g. '2 hours
    ago') depending on the source/actor. Only pass through values Postgres can parse
    as a timestamptz; drop anything else rather than let one bad row fail the whole
    chunk insert batch."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return str(value)
    except (ValueError, TypeError):
        return None


def _build_situation_query(ml_prediction, latest_indicators: dict, has_price_data: bool) -> str:
    """Describe the CURRENT technical/market situation in plain language, used to
    retrieve relevant book-derived strategy principles - deliberately about the
    situation, not the company, since the same principle (e.g. "cut losses fast")
    applies across many different tickers in the same technical state."""
    if not has_price_data:
        return (
            "No verified price data is available for this stock, high uncertainty, "
            "unknown risk profile, cautious decision-making under incomplete information"
        )

    rsi = latest_indicators.get("rsi_14")
    macd_hist = latest_indicators.get("macd_hist")
    bollinger_position = latest_indicators.get("bollinger_position")

    descriptors = [f"ML signal is {ml_prediction.signal} with confidence {ml_prediction.confidence:.2f}"]
    if rsi is not None:
        if rsi < 30:
            descriptors.append(f"oversold RSI at {rsi:.0f}")
        elif rsi > 70:
            descriptors.append(f"overbought RSI at {rsi:.0f}")
        else:
            descriptors.append(f"neutral RSI at {rsi:.0f}")
    if macd_hist is not None:
        descriptors.append("bullish MACD momentum" if macd_hist > 0 else "bearish MACD momentum")
    if bollinger_position is not None:
        if bollinger_position > 0.85:
            descriptors.append("price near upper Bollinger band")
        elif bollinger_position < 0.15:
            descriptors.append("price near lower Bollinger band")

    return "Stock technical situation: " + ", ".join(descriptors)


def _get_or_create_stock(ticker: str, name: str | None) -> dict:
    supabase = get_supabase()
    ticker = ticker.upper().strip()

    existing = supabase.table("stocks").select("*").eq("ticker", ticker).limit(1).execute()
    if existing.data:
        return existing.data[0]

    inserted = (
        supabase.table("stocks")
        .insert({"ticker": ticker, "name": name or ticker})
        .execute()
    )
    return inserted.data[0]


async def _fetch_and_store_price_history_async(stock_id: str, ticker: str, output_size: int) -> list[dict]:
    supabase = get_supabase()

    fresh_bars: list[dict] = []
    try:
        fresh_bars = await fetch_recent_bars(ticker, interval="5min", output_size=output_size)
    except MarketDataUnconfigured as e:
        logger.warning("Market data not configured (%s) - using stored price_history only.", e)
    except Exception as e:  # noqa: BLE001
        logger.warning("Market data fetch failed for %s: %s - using stored price_history only.", ticker, e)

    if fresh_bars:
        enriched = compute_indicators(fresh_bars)
        rows = [
            {
                "stock_id": stock_id,
                "ts": bar["ts"].isoformat() if hasattr(bar["ts"], "isoformat") else bar["ts"],
                **{k: v for k, v in bar.items() if k != "ts"},
            }
            for bar in enriched
        ]
        try:
            supabase.table("price_history").upsert(rows, on_conflict="stock_id,ts").execute()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to upsert price_history for %s: %s", ticker, e)

    # Read back the most recent window from the DB (covers both the fresh-fetch and
    # stored-only fallback paths with one code path).
    stored = (
        supabase.table("price_history")
        .select("*")
        .eq("stock_id", stock_id)
        .order("ts", desc=True)
        .limit(max(output_size, 30))
        .execute()
    )
    rows = list(reversed(stored.data or []))  # oldest-first
    return rows


async def _maybe_scrape_news(stock_id: str, ticker: str, name: str) -> None:
    """Best-effort news scraping via Firecrawl + Apify, only if the stored corpus is stale.
    Any failure (unconfigured key, network error) is logged and swallowed - the pipeline
    continues on stale/absent chunks rather than failing the whole recommendation."""
    supabase = get_supabase()
    settings = get_settings()

    latest = (
        supabase.table("document_chunks")
        .select("scraped_at")
        .eq("stock_id", stock_id)
        .order("scraped_at", desc=True)
        .limit(1)
        .execute()
    )
    if latest.data:
        last_scraped = datetime.fromisoformat(latest.data[0]["scraped_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - last_scraped < timedelta(hours=settings.news_rescrape_interval_hours):
            return  # still fresh, skip scraping

    # Run both scrapers concurrently - Apify's search run alone can take up to ~90s
    # (see apify_client.MAX_POLL_ATTEMPTS), so waiting for Firecrawl first would just
    # add dead time in front of it for no benefit.
    firecrawl_result, apify_result = await asyncio.gather(
        firecrawl_client.search_news(name),
        apify_client.search_news(name),
        return_exceptions=True,
    )

    articles: list[tuple[dict, str]] = []  # (article, source)
    if isinstance(firecrawl_result, BaseException):
        logger.info("Firecrawl scrape skipped/failed for %s: %s", ticker, firecrawl_result)
    else:
        articles += [(a, "firecrawl") for a in firecrawl_result]
    if isinstance(apify_result, BaseException):
        logger.info("Apify scrape skipped/failed for %s: %s", ticker, apify_result)
    else:
        articles += [(a, "apify") for a in apify_result]

    if not articles:
        return

    chunk_rows = []
    for article, source in articles:
        chunks = chunk_text(article.get("content", ""))
        for idx, chunk in enumerate(chunks):
            chunk_rows.append(
                {
                    "stock_id": stock_id,
                    "source": source,
                    "source_url": article.get("url"),
                    "title": article.get("title"),
                    "published_at": _safe_iso_date(article.get("published_at")),
                    "chunk_text": chunk,
                    "chunk_index": idx,
                }
            )

    if not chunk_rows:
        return

    try:
        embeddings = embed_texts([r["chunk_text"] for r in chunk_rows])
        for row, emb in zip(chunk_rows, embeddings):
            row["embedding"] = emb
        supabase.table("document_chunks").insert(chunk_rows).execute()
        logger.info("Stored %d new document chunks for %s", len(chunk_rows), ticker)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to embed/store document chunks for %s: %s", ticker, e)


async def analyze_stock(
    ticker: str, triggered_by: TriggeredBy, name: str | None = None
) -> dict:
    supabase = get_supabase()
    ticker = ticker.upper().strip()

    stock = _get_or_create_stock(ticker, name)
    stock_id = stock["id"]
    display_name = stock["name"]

    output_size = 30 if triggered_by == "scheduled" else 100
    price_rows = await _fetch_and_store_price_history_async(stock_id, ticker, output_size)
    has_price_data = bool(price_rows)

    # ML signal
    ml_prediction = None
    latest_indicators: dict = {}
    if price_rows:
        df = pd.DataFrame(price_rows)
        df = df.sort_values("ts").reset_index(drop=True)
        df = build_feature_frame(df)
        feature_vector = latest_feature_vector(df)
        latest_indicators = df.iloc[-1].to_dict()
        ml_prediction = get_model_service().predict(feature_vector)
    else:
        ml_prediction = get_model_service().predict(None)

    # News ingestion (best-effort, rate-limited by staleness check) + RAG retrieval
    await _maybe_scrape_news(stock_id, ticker, display_name)
    retrieved_chunks = retrieve_relevant_chunks(stock_id, f"{display_name} {ticker} recent news and outlook")

    # Strategy knowledge retrieval: matched against the current technical situation
    # (not the company), so the same book principle can surface for any ticker in a
    # similar state. See scripts/seed_strategy_knowledge.py for the source material.
    situation_query = _build_situation_query(ml_prediction, latest_indicators, has_price_data)
    retrieved_strategies = retrieve_relevant_strategies(situation_query)

    # Guardrails + Groq synthesis
    system_prompt, guardrail_rules = assemble_system_prompt()
    user_message = build_user_message(
        ticker=ticker,
        ml_signal=ml_prediction.signal,
        ml_predicted_return=ml_prediction.predicted_return,
        ml_confidence=ml_prediction.confidence,
        ml_is_heuristic=ml_prediction.is_heuristic,
        latest_indicators=latest_indicators,
        retrieved_chunks=retrieved_chunks,
        retrieved_strategies=retrieved_strategies,
        has_price_data=has_price_data,
    )

    result = generate_recommendation(system_prompt, user_message)
    passed, violations = validate_output(result["recommendation"], result["reasoning"])
    if not passed:
        logger.info("Guardrail violation(s) %s for %s, re-prompting once.", violations, ticker)
        corrective_user_message = (
            user_message
            + f"\n\nYour previous response violated these rules: {violations}. "
            "Revise your response to strictly comply, still as the same JSON format."
        )
        result = generate_recommendation(system_prompt, corrective_user_message)
        passed, violations = validate_output(result["recommendation"], result["reasoning"])
        if not passed:
            result["reasoning"] = apply_fallback(result["reasoning"], violations)

    record = {
        "stock_id": stock_id,
        "ml_signal": ml_prediction.signal,
        "ml_predicted_return": ml_prediction.predicted_return,
        "ml_confidence": ml_prediction.confidence,
        "final_recommendation": result["recommendation"],
        "reasoning": result["reasoning"],
        "guardrails_applied": [r["rule_key"] for r in guardrail_rules],
        "context_snapshot": {
            "has_price_data": has_price_data,
            "latest_indicators": {k: (v if not hasattr(v, "isoformat") else v.isoformat()) for k, v in latest_indicators.items()},
            "retrieved_chunk_ids": [c.get("id") for c in retrieved_chunks],
            "strategies_considered": [
                {
                    "book_title": s.get("book_title"),
                    "author": s.get("author"),
                    "topic": s.get("topic"),
                    "content": s.get("content"),
                    "similarity": s.get("similarity"),
                }
                for s in retrieved_strategies
            ],
            "ml": ml_prediction.to_dict(),
        },
        "triggered_by": triggered_by,
    }
    inserted = supabase.table("recommendations").insert(record).execute()
    saved = inserted.data[0]
    saved["ticker"] = ticker

    # Keep tracked_stocks.last_refreshed_at current if this stock is being tracked.
    supabase.table("tracked_stocks").update({"last_refreshed_at": datetime.now(timezone.utc).isoformat()}).eq(
        "stock_id", stock_id
    ).execute()

    return saved
