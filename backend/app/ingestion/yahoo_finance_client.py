"""Yahoo Finance fallback market-data source, via the (unofficial, free, no-API-key)
`yfinance` library. Used only for markets Infoway's current plan doesn't have real price
data for (India, Japan - see market_data_client.MARKETS) - Infoway stays the primary
source for US/China/Hong Kong since it's an official, stable API.

Confirmed working live (2026-09-22): daily AND 5-minute intraday bars for NSE-listed
India stocks (e.g. TATASTEEL.NS, RELIANCE.NS) and Tokyo-listed Japan stocks (e.g. 7203.T),
no signup or key required.

Caveat: this is an unofficial API (yfinance scrapes Yahoo's internal endpoints), so it
can break or get rate-limited without notice - if that happens, this module's errors
propagate up through the same graceful-degradation path as every other ingestion source
(caught in analyze_stock.py, falls back to no price data rather than crashing).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timezone
from typing import Any

logger = logging.getLogger(__name__)

# Infoway suffix -> Yahoo Finance suffix, for the markets we fall back to Yahoo for.
YAHOO_SUFFIX_MAP = {
    ".IN": ".NS",  # NSE (India's more liquid exchange; BSE would be .BO)
    ".JP": ".T",  # Tokyo Stock Exchange
}

# Our interval keys -> yfinance interval strings. yfinance limits intraday history to
# the last ~60 days regardless of requested range, which is far more than this app needs.
YAHOO_INTERVAL = {
    "5min": "5m",
    "15min": "15m",
    "30min": "30m",
    "1h": "1h",
    "1day": "1d",
}


class YahooFinanceError(Exception):
    pass


def supports_symbol(infoway_symbol: str) -> bool:
    """True if this ticker's market suffix is one we route to Yahoo instead of Infoway."""
    return any(infoway_symbol.upper().endswith(suffix) for suffix in YAHOO_SUFFIX_MAP)


def _to_yahoo_symbol(infoway_symbol: str) -> str:
    symbol = infoway_symbol.upper()
    for infoway_suffix, yahoo_suffix in YAHOO_SUFFIX_MAP.items():
        if symbol.endswith(infoway_suffix):
            return symbol[: -len(infoway_suffix)] + yahoo_suffix
    return symbol


def _fetch_sync(yahoo_symbol: str, interval: str, output_size: int) -> list[dict[str, Any]]:
    import yfinance as yf

    yf_interval = YAHOO_INTERVAL.get(interval)
    if yf_interval is None:
        raise YahooFinanceError(f"Unsupported interval '{interval}' for Yahoo Finance fallback")

    # yfinance wants a `period` (lookback window), not a bar count - pick one generous
    # enough to contain output_size bars, capped to what intraday data actually allows.
    if yf_interval.endswith("m") or yf_interval.endswith("h"):
        period = "5d" if output_size <= 200 else "1mo"
    else:
        # ~500 daily bars needs a few years of lookback.
        period = "3y" if output_size > 250 else "1y"

    ticker = yf.Ticker(yahoo_symbol)
    hist = ticker.history(period=period, interval=yf_interval)
    if hist.empty:
        return []

    hist = hist.tail(output_size)
    bars = []
    for ts, row in hist.iterrows():
        py_ts = ts.to_pydatetime()
        if py_ts.tzinfo is None:
            py_ts = py_ts.replace(tzinfo=timezone.utc)
        else:
            py_ts = py_ts.astimezone(timezone.utc)
        bars.append(
            {
                "ts": py_ts,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,  # NaN check
            }
        )
    return bars


async def fetch_recent_bars(infoway_symbol: str, interval: str, output_size: int) -> list[dict[str, Any]]:
    """Same return shape as market_data_client.fetch_recent_bars (oldest-first bar dicts).
    Runs the blocking yfinance call in a thread so it doesn't stall the event loop."""
    yahoo_symbol = _to_yahoo_symbol(infoway_symbol)
    try:
        bars = await asyncio.to_thread(_fetch_sync, yahoo_symbol, interval, output_size)
    except Exception as e:  # noqa: BLE001 - yfinance can raise a variety of exception types
        raise YahooFinanceError(f"Yahoo Finance fetch failed for {yahoo_symbol}: {e}") from e

    if not bars:
        logger.warning("Yahoo Finance returned no bars for %s (from %s)", yahoo_symbol, infoway_symbol)
    return bars
