"""Market data client for Infoway (https://infoway.io/, docs at https://docs.infoway.io/) -
real OHLCV price data, kept separate from Firecrawl/Apify (which only ever supply
news/sentiment text, never price ticks).

API shape (confirmed against the live API, not just docs):
- Base URL: https://data.infoway.io
- Auth: API key in the `apiKey` request header (not a query param).
- Candles: POST /stock/v2/batch_kline, body {klineType, klineNum, codes}. codes are
  comma-separated tickers with a market suffix (US stocks: "AAPL.US"). klineType maps
  a granularity to an int (2 = 5min, 8 = daily - see KLINE_TYPE below). Returns each
  ticker's bars newest-first; max 500 bars and 100 codes per call.
- Symbol search: GET /common/basic/symbols?type=STOCK_US (or STOCK_CN/STOCK_HK) returns
  the *entire* symbol list for that market in one call (no free-text query param) - we
  fetch each market once and cache it in memory, then filter client-side, rather than
  re-fetching per keystroke.
- Multi-market: symbol search covers US (.US, ~14.8k), China (.SZ/.SH, ~5.6k), Hong Kong
  (.HK, ~4.2k), India (.IN, ~5.6k) and Japan (.JP, ~3.9k). Candle data for US/China/Hong
  Kong goes through Infoway directly (confirmed working). Infoway's candle endpoint does
  NOT work for India/Japan on this plan - returns "All product not exists" for every
  ticker tested, including highly liquid ones (TCS, RELIANCE, INFY at .IN) - so those two
  markets are instead routed to the free Yahoo Finance fallback (yahoo_finance_client.py,
  no API key required), confirmed working for both daily and 5-minute intraday bars.

Note: Infoway issues a 7-day free trial key by default - if calls start failing with
an auth error after working previously, the trial may have expired and the key may
need to be upgraded/renewed at https://infoway.io/.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.ingestion import yahoo_finance_client

logger = logging.getLogger(__name__)

INFOWAY_BASE = "https://data.infoway.io"

# klineType mapping per Infoway docs: 1=1min, 2=5min, 3=15min, 4=30min, 5=1h, 6=2h, 7=4h, 8=daily.
KLINE_TYPE = {
    "1min": 1,
    "5min": 2,
    "15min": 3,
    "30min": 4,
    "1h": 5,
    "1day": 8,
}
MAX_KLINE_NUM = 500  # Infoway's per-call cap

# All markets offered in search. label = shown in the UI; has_price_data = whether
# fetch_recent_bars actually works for this market (confirmed by live testing). US/China/
# Hong Kong go through Infoway directly; India/Japan route through the free Yahoo Finance
# fallback instead (see yahoo_finance_client.py) since Infoway's plan doesn't cover them.
MARKETS: dict[str, tuple[str, bool]] = {
    "STOCK_US": ("US", True),
    "STOCK_CN": ("China", True),
    "STOCK_HK": ("Hong Kong", True),
    "STOCK_IN": ("India", True),
    "STOCK_JP": ("Japan", True),
}

_symbol_cache: dict[str, list[dict[str, Any]]] = {}
_symbol_cache_fetched_at: dict[str, float] = {}
_SYMBOL_CACHE_TTL_SECONDS = 24 * 60 * 60


class MarketDataError(Exception):
    pass


class MarketDataUnconfigured(MarketDataError):
    """Raised when no market data API key has been configured."""


def _require_key() -> str:
    settings = get_settings()
    if not settings.has_market_data_key:
        raise MarketDataUnconfigured(
            "MARKET_DATA_API_KEY is not set in the project's .env file. Get a key from https://infoway.io/"
        )
    return settings.market_data_api_key


def _to_infoway_symbol(ticker: str) -> str:
    """Non-US tickers already carry their market suffix (from search results); a bare
    ticker with no suffix is assumed US, matching the app's original US-only convention."""
    ticker = ticker.upper().strip()
    return ticker if "." in ticker else f"{ticker}.US"


def _from_infoway_symbol(symbol: str) -> str:
    """Strip the .US suffix for display/storage (existing "AAPL" convention); keep
    non-US suffixes (.SZ/.SH/.HK) since bare numeric codes would otherwise collide
    across markets and aren't a recognizable ticker on their own."""
    return symbol.split(".")[0] if symbol.endswith(".US") else symbol


async def _fetch_market_symbols(market_type: str) -> list[dict[str, Any]]:
    now = time.time()
    cached = _symbol_cache.get(market_type)
    if cached is not None and (now - _symbol_cache_fetched_at.get(market_type, 0)) < _SYMBOL_CACHE_TTL_SECONDS:
        return cached

    api_key = _require_key()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{INFOWAY_BASE}/common/basic/symbols",
            headers={"apiKey": api_key},
            params={"type": market_type},
        )
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("ret") != 200:
        raise MarketDataError(f"Infoway symbol list error ({market_type}): {payload.get('msg')}")

    symbols = payload.get("data", [])
    _symbol_cache[market_type] = symbols
    _symbol_cache_fetched_at[market_type] = now
    return symbols


def _company_key(name: str) -> str:
    """Loose company-identity key so e.g. "Infosys" (India, no data) and "Infosys"
    (US ADR, has data) are recognized as the same company for the suggestion check -
    strips common suffixes and punctuation, keeps just the leading word(s)."""
    name = name.lower()
    for suffix in (" limited", " ltd", " ltd.", " inc", " inc.", " corp", " corporation", " co.", " company", " plc", " holdings", " group"):
        name = name.replace(suffix, "")
    return "".join(ch for ch in name if ch.isalnum())[:20]


async def search_symbol(query: str) -> list[dict[str, Any]]:
    """Free-text ticker/name lookup across every market Infoway lists (US, China, Hong
    Kong, India, Japan), proxied so the frontend never needs the market-data key
    directly. Infoway has no server-side search, so this fetches (and caches per-market)
    each market's full symbol list once and filters client-side.

    India and Japan listings are included even though their price data doesn't work on
    this plan (see MARKETS) - hiding them entirely left searches like "Tata" with zero
    results and pushed users into a blind "analyze anyway" fallback that silently
    produced a misleading response. Each result now carries `has_price_data` so the UI
    can show the real company while being upfront about the limitation, and results with
    working price data are ranked above otherwise-equal matches so a supported
    alternative (e.g. an ADR) surfaces first when one exists.

    Markets are fetched sequentially (not concurrently) with a small stagger - Infoway's
    API returned 429s under rapid-fire concurrent requests during testing.
    """
    q = query.strip().lower()
    if not q:
        return []

    matches: list[dict[str, Any]] = []
    market_items = list(MARKETS.items())
    for market_type, (label, has_price_data) in market_items:
        try:
            symbols = await _fetch_market_symbols(market_type)
        except MarketDataError as e:
            logger.warning("Skipping %s in symbol search: %s", market_type, e)
            continue
        for s in symbols:
            if q in (s.get("symbol") or "").lower() or q in (s.get("name_en") or "").lower():
                matches.append({**s, "_market_label": label, "_has_price_data": has_price_data})
        if market_type != market_items[-1][0]:
            await asyncio.sleep(0.3)

    def rank(s: dict[str, Any]) -> tuple[int, int, str]:
        symbol = (s.get("symbol") or "").lower()
        name = (s.get("name_en") or s.get("name_cn") or "").lower()
        bare_symbol = symbol.split(".")[0]
        if bare_symbol == q:
            match_score = 0  # exact ticker match, e.g. "aapl" -> AAPL.US
        elif symbol.startswith(q) or bare_symbol.startswith(q):
            match_score = 1  # ticker prefix match
        elif name.startswith(q):
            match_score = 2  # company name prefix match, e.g. "apple" -> Apple Inc
        else:
            match_score = 3  # substring match somewhere in symbol/name
        return (match_score, 0 if s["_has_price_data"] else 1, name)

    matches.sort(key=rank)

    # For each no-data match, note whether a same-company alternative with working
    # price data also matched (e.g. Infosys's India listing vs its US ADR) - lets the
    # UI say "try INFY.US instead" rather than a flat "unsupported".
    supported_keys = {_company_key(s.get("name_en") or s.get("name_cn") or "") for s in matches if s["_has_price_data"]}

    results = []
    for s in matches[:20]:
        if not s.get("symbol"):
            continue
        name = s.get("name_en") or s.get("name_cn") or s["symbol"]
        has_data = s["_has_price_data"]
        alt_ticker = None
        if not has_data and _company_key(name) in supported_keys:
            alt = next(
                (m for m in matches if m["_has_price_data"] and _company_key(m.get("name_en") or m.get("name_cn") or "") == _company_key(name)),
                None,
            )
            if alt:
                alt_ticker = _from_infoway_symbol(alt["symbol"])
        results.append(
            {
                "ticker": _from_infoway_symbol(s["symbol"]),
                "name": name,
                "exchange": s["_market_label"],
                "has_price_data": has_data,
                "alternative_ticker": alt_ticker,
            }
        )
    return results[:15]


async def fetch_recent_bars(
    ticker: str, interval: str = "5min", output_size: int = 100
) -> list[dict[str, Any]]:
    """Fetch recent OHLCV bars for a ticker. Returns oldest-first list of bar dicts.

    Routes to Yahoo Finance instead of Infoway for markets Infoway doesn't have working
    price data for on this plan (India, Japan - see yahoo_finance_client.YAHOO_SUFFIX_MAP).
    """
    symbol = _to_infoway_symbol(ticker)

    if yahoo_finance_client.supports_symbol(symbol):
        return await yahoo_finance_client.fetch_recent_bars(symbol, interval, output_size)

    api_key = _require_key()
    kline_type = KLINE_TYPE.get(interval)
    if kline_type is None:
        raise MarketDataError(f"Unsupported interval '{interval}' for Infoway (supported: {list(KLINE_TYPE)})")

    kline_num = min(output_size, MAX_KLINE_NUM)

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{INFOWAY_BASE}/stock/v2/batch_kline",
            headers={"apiKey": api_key, "Content-Type": "application/json"},
            json={"klineType": kline_type, "klineNum": kline_num, "codes": symbol},
        )
        resp.raise_for_status()
        payload = resp.json()

    if payload.get("ret") != 200:
        raise MarketDataError(f"Infoway error for {ticker}: {payload.get('msg')}")

    data = payload.get("data") or []
    if not data:
        return []
    resp_list = data[0].get("respList") or []  # newest-first

    bars = []
    for r in reversed(resp_list):  # -> oldest-first
        bars.append(
            {
                "ts": datetime.fromtimestamp(int(r["t"]), tz=timezone.utc),
                "open": float(r["o"]),
                "high": float(r["h"]),
                "low": float(r["l"]),
                "close": float(r["c"]),
                "volume": int(float(r.get("v") or 0)),
            }
        )
    return bars
