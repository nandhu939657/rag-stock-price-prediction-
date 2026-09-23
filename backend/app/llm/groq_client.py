"""Groq LLM call for final recommendation synthesis. Requests JSON-mode output and
falls back to a regex extraction if parsing fails, so a malformed response never
crashes the pipeline - it just degrades to a flagged 'hold'.
"""
from __future__ import annotations

import json
import logging
import re

from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def _parse_response(raw_text: str) -> dict:
    try:
        parsed = json.loads(raw_text)
        rec = str(parsed.get("recommendation", "")).lower().strip()
        reasoning = str(parsed.get("reasoning", "")).strip()
        if rec in ("buy", "sell", "hold") and reasoning:
            return {"recommendation": rec, "reasoning": reasoning}
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: regex-extract a buy/sell/hold token from raw text.
    match = re.search(r"\b(buy|sell|hold)\b", raw_text, re.IGNORECASE)
    rec = match.group(1).lower() if match else "hold"
    logger.warning("Groq response was not valid JSON; fell back to regex extraction -> %s", rec)
    return {
        "recommendation": rec,
        "reasoning": raw_text.strip() or "Model response could not be parsed; defaulted to hold as a precaution. This is not financial advice.",
        "is_fallback": True,
        "fallback_reason": "unparseable_response",
    }


def generate_recommendation(system_prompt: str, user_message: str) -> dict:
    settings = get_settings()
    client = _get_client()

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            # openai/gpt-oss-* models on Groq are reasoning models that spend tokens on
            # hidden chain-of-thought before emitting the JSON body - too low a budget
            # here truncates before any JSON is produced and the call fails validation.
            # Bumped from 1200 alongside the longer required reasoning structure (a real
            # causal explanation runs longer than a bare restatement of the indicators).
            max_tokens=1600,
        )
        raw_text = completion.choices[0].message.content or ""
    except Exception as e:  # noqa: BLE001
        logger.error("Groq call failed: %s", e)
        is_quota = "rate_limit_exceeded" in str(e) or "429" in str(e)
        return {
            "recommendation": "hold",
            "reasoning": "The analysis service is temporarily unavailable, defaulting to hold as a precaution. This is not financial advice.",
            "is_fallback": True,
            "fallback_reason": "quota_exhausted" if is_quota else "service_error",
        }

    return _parse_response(raw_text)
