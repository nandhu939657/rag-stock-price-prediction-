from __future__ import annotations

from fastapi import APIRouter

from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/api/stocks", tags=["recommendations"])


@router.get("/tracked")
async def list_tracked():
    supabase = get_supabase()

    tracked = (
        supabase.table("tracked_stocks")
        .select("stock_id, is_tracked, added_at, last_refreshed_at, stocks(ticker, name)")
        .eq("is_tracked", True)
        .execute()
    )
    rows = tracked.data or []

    result = []
    for row in rows:
        stock_info = row.get("stocks") or {}
        stock_id = row["stock_id"]

        latest = (
            supabase.table("recommendations")
            .select("*")
            .eq("stock_id", stock_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_rec = latest.data[0] if latest.data else None
        if latest_rec:
            latest_rec["ticker"] = stock_info.get("ticker")

        # Compact recent-close series for the dashboard sparkline (oldest-first).
        closes = supabase.rpc("get_recent_closes", {"target_stock_id": stock_id, "bar_count": 12}).execute()
        recent_closes = [float(r["close"]) for r in reversed(closes.data or []) if r.get("close") is not None]

        result.append(
            {
                "stock_id": stock_id,
                "ticker": stock_info.get("ticker"),
                "name": stock_info.get("name"),
                "is_tracked": row["is_tracked"],
                "added_at": row["added_at"],
                "last_refreshed_at": row["last_refreshed_at"],
                "latest_recommendation": latest_rec,
                "recent_closes": recent_closes,
            }
        )

    return result
