from __future__ import annotations

from fastapi import APIRouter

from app.db.supabase_client import get_supabase

router = APIRouter(prefix="/api", tags=["guardrails"])


@router.get("/guardrails")
async def list_guardrails():
    """Active guardrail + domain-fact rules, for the Settings/About page - lets the
    user see exactly what constraints are being injected into every Groq call."""
    supabase = get_supabase()
    resp = (
        supabase.table("knowledge_base")
        .select("rule_key, category, content, severity, is_active")
        .eq("is_active", True)
        .order("category")
        .execute()
    )
    return resp.data or []


@router.get("/strategies")
async def list_strategies():
    """The book-derived strategy knowledge library (see scripts/seed_strategy_knowledge.py
    and app/rag/retriever.retrieve_relevant_strategies), grouped by book for the
    Settings/About page - lets the user see exactly which principles the RAG pipeline
    can draw on when reasoning about a stock's technical situation."""
    supabase = get_supabase()
    resp = (
        supabase.table("strategy_knowledge")
        .select("id, book_title, author, topic, content")
        .order("book_title")
        .execute()
    )
    rows = resp.data or []

    books: dict[str, dict] = {}
    for r in rows:
        title = r["book_title"]
        if title not in books:
            books[title] = {"book_title": title, "author": r["author"], "principles": []}
        books[title]["principles"].append({"topic": r["topic"], "content": r["content"]})

    return {"books": list(books.values()), "total_principles": len(rows)}
