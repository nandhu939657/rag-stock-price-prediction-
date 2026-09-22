"""pgvector similarity search over document_chunks (scraped news) and strategy_knowledge
(book-derived principles), via the match_document_chunks / match_strategy_knowledge
Postgres functions - keeps the vector math in the DB instead of pulling every row into
Python.
"""
from __future__ import annotations

import logging

from app.db.supabase_client import get_supabase
from app.ingestion.embeddings import embed_query

logger = logging.getLogger(__name__)


def retrieve_relevant_chunks(stock_id: str, query: str, match_count: int = 5) -> list[dict]:
    """News/article chunks scoped to one stock - see supabase/migrations/0005."""
    supabase = get_supabase()
    try:
        query_embedding = embed_query(query)
    except Exception as e:  # noqa: BLE001
        logger.warning("Embedding query failed, skipping RAG retrieval: %s", e)
        return []

    try:
        resp = supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "target_stock_id": stock_id,
                "match_count": match_count,
            },
        ).execute()
        return resp.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("pgvector retrieval failed for stock_id=%s: %s", stock_id, e)
        return []


def retrieve_relevant_strategies(query: str, match_count: int = 4) -> list[dict]:
    """Book-derived strategy/principle knowledge, matched against the CURRENT technical
    situation (not the company) - see supabase/migrations/0009. Not scoped to a stock:
    the same principle (e.g. "cut losses fast") can be relevant to any ticker."""
    supabase = get_supabase()
    try:
        query_embedding = embed_query(query)
    except Exception as e:  # noqa: BLE001
        logger.warning("Embedding query failed, skipping strategy retrieval: %s", e)
        return []

    try:
        resp = supabase.rpc(
            "match_strategy_knowledge",
            {"query_embedding": query_embedding, "match_count": match_count},
        ).execute()
        return resp.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning("Strategy knowledge retrieval failed: %s", e)
        return []
