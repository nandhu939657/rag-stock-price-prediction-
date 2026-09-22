from __future__ import annotations

from fastapi import APIRouter

from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/api/stocks", tags=["overview"])


@router.get("/movers")
async def movers(limit: int = 5):
    """Top gainers/losers among stocks that have been analyzed in this app (scoped to
    our own data, not a full-market scan) - see get_price_movers() in the DB."""
    supabase = get_supabase()
    resp = supabase.rpc("get_price_movers", {}).execute()
    rows = resp.data or []

    positive = [r for r in rows if (r.get("change_pct") or 0) > 0]
    negative = [r for r in rows if (r.get("change_pct") or 0) < 0]

    gainers = sorted(positive, key=lambda r: r["change_pct"], reverse=True)[:limit]
    losers = sorted(negative, key=lambda r: r["change_pct"])[:limit]

    return {"gainers": gainers, "losers": losers, "total_analyzed": len(rows)}
