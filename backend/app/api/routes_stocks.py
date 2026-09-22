from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.db.supabase_client import get_supabase
from app.ingestion.market_data_client import MarketDataUnconfigured, search_symbol
from app.models_schemas import AnalyzeRequest, RecommendationOut, SymbolSearchResult
from app.pipeline.analyze_stock import analyze_stock

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search", response_model=list[SymbolSearchResult])
async def search(q: str):
    if not q or len(q.strip()) < 1:
        raise HTTPException(400, "q is required")
    try:
        results = await search_symbol(q.strip())
    except MarketDataUnconfigured as e:
        raise HTTPException(503, str(e)) from e
    return results[:10]


@router.post("/analyze")
async def analyze(payload: AnalyzeRequest):
    if not payload.ticker or not payload.ticker.strip():
        raise HTTPException(400, "ticker is required")
    try:
        record = await analyze_stock(payload.ticker, triggered_by="on_demand", name=payload.name)
    except Exception as e:  # noqa: BLE001
        logger.exception("Analyze failed for %s", payload.ticker)
        raise HTTPException(500, f"Analysis failed: {e}") from e
    return record


@router.post("/{ticker}/track")
async def track(ticker: str):
    supabase = get_supabase()
    ticker = ticker.upper().strip()

    # Ensure the stock is analyzed at least once so there's an immediate recommendation.
    try:
        record = await analyze_stock(ticker, triggered_by="on_demand")
    except Exception as e:  # noqa: BLE001
        logger.exception("Initial analysis failed while tracking %s", ticker)
        raise HTTPException(500, f"Could not analyze {ticker}: {e}") from e

    from datetime import datetime, timezone

    stock_id = record["stock_id"]
    now = datetime.now(timezone.utc).isoformat()
    # analyze_stock() above tries to stamp last_refreshed_at, but no tracked_stocks row
    # exists yet on a first-time track - set it here too so the UI doesn't show "pending"
    # until the next scheduled refresh.
    existing = supabase.table("tracked_stocks").select("*").eq("stock_id", stock_id).limit(1).execute()
    if existing.data:
        supabase.table("tracked_stocks").update(
            {"is_tracked": True, "removed_at": None, "last_refreshed_at": now}
        ).eq("stock_id", stock_id).execute()
    else:
        supabase.table("tracked_stocks").insert(
            {"stock_id": stock_id, "is_tracked": True, "last_refreshed_at": now}
        ).execute()

    return {"status": "tracked", "ticker": ticker, "stock_id": stock_id}


@router.delete("/{ticker}/track")
async def untrack(ticker: str):
    supabase = get_supabase()
    ticker = ticker.upper().strip()

    stock = supabase.table("stocks").select("id").eq("ticker", ticker).limit(1).execute()
    if not stock.data:
        raise HTTPException(404, f"{ticker} not found")
    stock_id = stock.data[0]["id"]

    from datetime import datetime, timezone

    supabase.table("tracked_stocks").update(
        {"is_tracked": False, "removed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("stock_id", stock_id).execute()

    return {"status": "untracked", "ticker": ticker}
