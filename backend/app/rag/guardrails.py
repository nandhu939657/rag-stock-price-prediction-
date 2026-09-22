"""Guardrail enforcement: rules stored in knowledge_base are (1) injected into every
Groq system prompt, and (2) checked post-generation as defense in depth, since LLMs
sometimes ignore instructions. Not a compliance guarantee - just the standard practical
two-layer pattern for a single-user tool.
"""
from __future__ import annotations

import logging
import re

from app.db.supabase_client import get_supabase
from app.rag.prompt_templates import build_system_prompt

logger = logging.getLogger(__name__)

DISCLAIMER_PATTERN = re.compile(r"not\s+financial\s+advice", re.IGNORECASE)
BANNED_PHRASES = [
    "guaranteed", "guarantee", "certain to", "sure thing", "100% ",
    "risk-free", "can't lose", "cannot lose",
]
FALLBACK_DISCLAIMER = (
    " (Note: this is not financial advice; past performance does not guarantee future results.)"
)


def fetch_active_guardrails() -> list[dict]:
    supabase = get_supabase()
    resp = (
        supabase.table("knowledge_base")
        .select("rule_key, content, severity")
        .eq("category", "guardrail")
        .eq("is_active", True)
        .execute()
    )
    return resp.data or []


def assemble_system_prompt() -> tuple[str, list[dict]]:
    rules = fetch_active_guardrails()
    return build_system_prompt(rules), rules


def validate_output(recommendation: str, reasoning: str) -> tuple[bool, list[str]]:
    """Returns (passed, violated_rule_keys)."""
    violations = []

    if not DISCLAIMER_PATTERN.search(reasoning):
        violations.append("mandatory_disclaimer")

    lower_reasoning = reasoning.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower_reasoning:
            violations.append("confidence_cap")
            break

    if recommendation not in ("buy", "sell", "hold"):
        violations.append("invalid_recommendation_value")

    return (len(violations) == 0, violations)


def apply_fallback(reasoning: str, violations: list[str]) -> str:
    """Programmatic fix-up when a second LLM attempt still violates a rule."""
    if "mandatory_disclaimer" in violations and not DISCLAIMER_PATTERN.search(reasoning):
        reasoning = reasoning.rstrip() + FALLBACK_DISCLAIMER
    return reasoning
