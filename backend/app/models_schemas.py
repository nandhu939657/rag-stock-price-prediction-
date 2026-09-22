from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    ticker: str
    name: str | None = None  # optional display name, used if the stock is new


class RecommendationOut(BaseModel):
    id: str
    stock_id: str
    ticker: str
    created_at: datetime
    ml_signal: Literal["up", "down", "flat"] | None
    ml_predicted_return: float | None
    ml_confidence: float | None
    final_recommendation: Literal["buy", "sell", "hold"]
    reasoning: str
    guardrails_applied: list[str]
    triggered_by: Literal["scheduled", "on_demand"]


class TrackedStockOut(BaseModel):
    stock_id: str
    ticker: str
    name: str
    is_tracked: bool
    added_at: datetime
    last_refreshed_at: datetime | None
    latest_recommendation: RecommendationOut | None


class SymbolSearchResult(BaseModel):
    ticker: str
    name: str
    exchange: str | None = None
    has_price_data: bool = True
    alternative_ticker: str | None = None


class HealthOut(BaseModel):
    status: str
    scheduler_running: bool
    last_run_at: datetime | None
    tracked_stock_count: int


class PriceBarOut(BaseModel):
    ts: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    sma_20: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None


class StockHistoryOut(BaseModel):
    ticker: str
    price_history: list[PriceBarOut]
    recommendations: list[RecommendationOut]
