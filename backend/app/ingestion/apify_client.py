"""Apify client - runs a Google Search actor for additional news/sentiment coverage,
complementing Firecrawl. https://docs.apify.com/api/v2

Default actor: apify/google-search-scraper (official, pay-per-usage - not one of the
"rent to run" community actors, which reject calls once their free trial expires).
Returns one dataset item per query/page, each with an `organicResults` array of
{title, url, description} - that's what search_news() flattens into article dicts.

Uses the async run -> poll -> fetch-dataset pattern rather than run-sync-get-dataset-items:
this actor's own run time (~45-90s for a real SERP fetch) exceeds what's reasonable to
hold a single synchronous HTTP request open for.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
POLL_INTERVAL_SECONDS = 5
# This runs inline with a user-facing "Analyze" click, so it needs a ceiling that still
# feels responsive. Observed real run times vary ~60-150s; capping at 90s means slow
# runs are simply skipped for that analysis (Firecrawl still contributes news context)
# rather than making the user wait minutes for a button click.
MAX_POLL_ATTEMPTS = 18  # ~90 seconds
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ApifyUnconfigured(Exception):
    pass


class ApifyRunFailed(Exception):
    pass


def _require_token() -> str:
    settings = get_settings()
    if not settings.has_apify_key:
        raise ApifyUnconfigured(
            "APIFY_API_TOKEN is not set in the project's .env file. Get one at https://apify.com/"
        )
    return settings.apify_api_token


async def search_news(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Run the configured Apify actor and return normalized {title, url, published_at,
    content} article dicts, flattened from the actor's per-page organicResults."""
    settings = get_settings()
    token = _require_token()
    actor_id = settings.apify_news_actor_id

    async with httpx.AsyncClient(timeout=30) as client:
        start_resp = await client.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs",
            params={"token": token},
            json={"queries": f"{query} stock news", "resultsPerPage": limit, "maxPagesPerQuery": 1},
        )
        start_resp.raise_for_status()
        run_id = start_resp.json()["data"]["id"]

        dataset_id = None
        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            status_resp = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}", params={"token": token})
            status_resp.raise_for_status()
            run_data = status_resp.json()["data"]
            if run_data["status"] in TERMINAL_STATUSES:
                if run_data["status"] != "SUCCEEDED":
                    raise ApifyRunFailed(f"Apify run {run_id} ended with status {run_data['status']}")
                dataset_id = run_data["defaultDatasetId"]
                break

        if dataset_id is None:
            raise ApifyRunFailed(f"Apify run {run_id} did not finish within the poll budget")

        items_resp = await client.get(f"{APIFY_BASE}/datasets/{dataset_id}/items", params={"token": token})
        items_resp.raise_for_status()
        pages = items_resp.json()

    results: list[dict[str, Any]] = []
    for page in pages:
        for r in page.get("organicResults", []):
            content = r.get("description") or ""
            url = r.get("url")
            if not content.strip() or not url:
                continue
            results.append(
                {
                    "title": r.get("title"),
                    "url": url,
                    "published_at": None,  # SERP results don't reliably carry publish dates
                    "content": content,
                }
            )
            if len(results) >= limit:
                return results
    return results
