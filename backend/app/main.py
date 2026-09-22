from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_guardrails, routes_history, routes_overview, routes_recommendations, routes_stocks
from app.config import get_settings
from app.db.supabase_client import get_supabase
from app.scheduler.refresh_job import get_last_run_at, is_scheduler_running, start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("Backend started.")
    yield
    stop_scheduler()


app = FastAPI(title="RAG Stock Advisor API", lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_stocks.router)
app.include_router(routes_recommendations.router)
app.include_router(routes_history.router)
app.include_router(routes_guardrails.router)
app.include_router(routes_overview.router)


@app.get("/api/health")
async def health():
    supabase = get_supabase()
    tracked = supabase.table("tracked_stocks").select("stock_id", count="exact").eq("is_tracked", True).execute()
    return {
        "status": "ok",
        "scheduler_running": is_scheduler_running(),
        "last_run_at": get_last_run_at(),
        "tracked_stock_count": tracked.count or 0,
    }
