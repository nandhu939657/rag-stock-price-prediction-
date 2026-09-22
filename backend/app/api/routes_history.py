from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/api/stocks", tags=["history"])


@router.get("/{ticker}/history")
async def history(ticker: str, price_limit: int = 100, recommendation_limit: int = 50):
    supabase = get_supabase()
    ticker = ticker.upper().strip()

    stock = supabase.table("stocks").select("id").eq("ticker", ticker).limit(1).execute()
    if not stock.data:
        raise HTTPException(404, f"{ticker} not found")
    stock_id = stock.data[0]["id"]

    price = (
        supabase.table("price_history")
        .select("ts, open, high, low, close, volume, sma_20, ema_20, rsi_14, macd, macd_signal, bollinger_upper, bollinger_lower")
        .eq("stock_id", stock_id)
        .order("ts", desc=True)
        .limit(price_limit)
        .execute()
    )
    recs = (
        supabase.table("recommendations")
        .select("*")
        .eq("stock_id", stock_id)
        .order("created_at", desc=True)
        .limit(recommendation_limit)
        .execute()
    )

    recommendations = recs.data or []
    for r in recommendations:
        r["ticker"] = ticker

    sources = (
        supabase.table("document_chunks")
        .select("id, source, source_url, title, published_at, chunk_text, scraped_at")
        .eq("stock_id", stock_id)
        .order("scraped_at", desc=True)
        .limit(30)
        .execute()
    )
    # Dedupe to one entry per article (source_url) - a long article can produce several
    # chunks, but the "News & Sources" panel should list articles, not raw chunks.
    seen_urls: set[str] = set()
    articles = []
    for row in sources.data or []:
        url = row.get("source_url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        articles.append(row)

    return {
        "ticker": ticker,
        "price_history": list(reversed(price.data or [])),
        "recommendations": recommendations,
        "sources": articles,
    }
