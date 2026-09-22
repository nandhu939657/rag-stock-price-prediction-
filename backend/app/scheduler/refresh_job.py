"""APScheduler job: every SCHEDULER_INTERVAL_MINUTES minutes, re-run the shared
analyze_stock pipeline for every currently tracked stock. Runs sequentially (not
concurrently) to stay rate-limit-friendly with the market data / Firecrawl / Apify APIs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.db.supabase_client import get_supabase
from app.pipeline.analyze_stock import analyze_stock

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_last_run_at: datetime | None = None


async def refresh_tracked_stocks() -> None:
    global _last_run_at
    supabase = get_supabase()

    tracked = (
        supabase.table("tracked_stocks")
        .select("stock_id, stocks(ticker, name)")
        .eq("is_tracked", True)
        .execute()
    )
    rows = tracked.data or []
    logger.info("Scheduled refresh: %d tracked stock(s)", len(rows))

    for row in rows:
        stock_info = row.get("stocks") or {}
        ticker = stock_info.get("ticker")
        if not ticker:
            continue
        try:
            await analyze_stock(ticker, triggered_by="scheduled", name=stock_info.get("name"))
            logger.info("Refreshed %s", ticker)
        except Exception as e:  # noqa: BLE001 - one stock failing must not stop the others
            logger.error("Failed to refresh %s: %s", ticker, e)

    _last_run_at = datetime.now(timezone.utc)


def get_last_run_at() -> datetime | None:
    return _last_run_at


def is_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    settings = get_settings()
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        refresh_tracked_stocks,
        "interval",
        minutes=settings.scheduler_interval_minutes,
        id="refresh_tracked_stocks",
        next_run_time=datetime.now(timezone.utc),  # run once immediately on startup too
    )
    _scheduler.start()
    logger.info("Scheduler started: refreshing tracked stocks every %d minute(s)", settings.scheduler_interval_minutes)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
