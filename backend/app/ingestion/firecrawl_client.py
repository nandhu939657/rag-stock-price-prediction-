"""Firecrawl client - searches the web and scrapes article content for a stock's
recent news, used only as RAG source text (never for price data).
https://docs.firecrawl.dev/
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


class FirecrawlUnconfigured(Exception):
    pass


def _require_key() -> str:
    settings = get_settings()
    if not settings.has_firecrawl_key:
        raise FirecrawlUnconfigured(
            "FIRECRAWL_API_KEY is not set in the project's .env file. Get one at https://www.firecrawl.dev/"
        )
    return settings.firecrawl_api_key


async def search_news(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the web for recent articles about `query` and return scraped markdown content.

    Returns a list of {title, url, published_at, content} dicts. Any per-result failure is
    swallowed (logged) so one bad source doesn't fail the whole ingestion step.
    """
    api_key = _require_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{FIRECRAWL_BASE}/search",
            headers=headers,
            json={
                "query": f"{query} stock news",
                "limit": limit,
                "scrapeOptions": {"formats": ["markdown"]},
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    results = []
    for item in payload.get("data", []):
        content = item.get("markdown") or item.get("description") or ""
        if not content.strip():
            continue
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "published_at": None,  # Firecrawl search doesn't reliably return publish dates
                "content": content,
            }
        )
    return results
