"""Prompt assembly for the Groq recommendation call. Guardrails live in the system
prompt (separate from scraped-text context) so injected instructions in a news article
can't easily override them.
"""
from __future__ import annotations

SYSTEM_PROMPT_HEADER = (
    "You are a stock analysis assistant for a single retail user's personal research tool. "
    "You MUST follow these rules at all times, with no exceptions:\n"
)

SYSTEM_PROMPT_FOOTER = (
    "\nBase your recommendation only on the ML signal, technical indicators, and retrieved "
    "news context provided in the user message. Do not invent facts not present there.\n"
    "\n"
    "Your reasoning must be genuine analysis, not a restatement of the input numbers. "
    "Never just list indicator values and slap a generic conclusion on the end (e.g. "
    '"RSI is 76, MACD is positive, mixed signals, so hold" is NOT acceptable - that '
    "restates data without explaining what it means or why it leads anywhere). Structure "
    "the reasoning as a short causal chain:\n"
    "1. What the technical picture concretely implies (not just the numbers - their "
    "standard meaning). Use correct, internally consistent interpretation: RSI below "
    "~30 or price near the lower Bollinger band is OVERSOLD, which typically signals "
    "fading downward momentum and a higher chance of a bounce (a bullish-leaning signal, "
    "not bearish); RSI above ~70 or price near the upper band is OVERBOUGHT, typically "
    "signalling a higher chance of a pullback (bearish-leaning); a positive/rising MACD "
    "histogram signals strengthening bullish momentum, a negative/falling one signals "
    "strengthening bearish momentum. If your conclusion runs against one of these "
    "standard readings (e.g. you see oversold conditions but still lean bearish), say so "
    "explicitly and explain why - never state an indicator's standard implication "
    "backwards.\n"
    "2. What the ML signal adds - does it agree or disagree with the technical picture, "
    "and how much weight its confidence level deserves.\n"
    "3. What the news context adds, and whether it reinforces or conflicts with the "
    "technical/ML picture.\n"
    "4. Which of the retrieved investing principles (if any) actually apply to this "
    "specific situation, and what they'd suggest - name the book/author when you use one "
    "(e.g. \"O'Neil's CANSLIM approach would flag the rising volume here as bullish "
    "confirmation\"). Skip a principle if it doesn't genuinely fit rather than forcing a "
    "mention - these are decision-support context, not a checklist to recite.\n"
    "5. The actual recommendation and the specific reason it follows from weighing 1-4 - "
    "if signals conflict, say which one you weighted more heavily and why, rather than "
    "defaulting to hold with an unexplained 'mixed signals' hand-wave.\n"
    "\n"
    "Respond ONLY with a JSON object of the form "
    '{"recommendation": "buy"|"sell"|"hold", "reasoning": "<3-7 sentence causal explanation '
    'following the structure above>"}. No text outside the JSON object.'
)


def build_system_prompt(guardrail_rules: list[dict]) -> str:
    hard = [r for r in guardrail_rules if r.get("severity") == "hard"]
    soft = [r for r in guardrail_rules if r.get("severity") == "soft"]
    lines = [f"- {r['content']}" for r in hard + soft]
    return SYSTEM_PROMPT_HEADER + "\n".join(lines) + SYSTEM_PROMPT_FOOTER


def build_user_message(
    ticker: str,
    ml_signal: str,
    ml_predicted_return: float,
    ml_confidence: float,
    ml_is_heuristic: bool,
    latest_indicators: dict,
    retrieved_chunks: list[dict],
    retrieved_strategies: list[dict] | None = None,
    has_price_data: bool = True,
) -> str:
    chunk_lines = []
    for c in retrieved_chunks:
        title = c.get("title") or "(untitled)"
        url = c.get("source_url") or ""
        published = c.get("published_at") or "unknown date"
        text = c.get("chunk_text", "")
        chunk_lines.append(f"- [{title}] ({published}, {url}): {text}")
    chunks_block = "\n".join(chunk_lines) if chunk_lines else "(no recent news retrieved)"

    strategy_lines = []
    for s in retrieved_strategies or []:
        strategy_lines.append(f"- [{s.get('book_title')} - {s.get('author')}] ({s.get('topic')}): {s.get('content')}")
    strategies_block = "\n".join(strategy_lines) if strategy_lines else "(no closely relevant principles retrieved)"

    heuristic_note = (
        " (heuristic fallback - no trained model or insufficient history, treat as low confidence)"
        if ml_is_heuristic
        else ""
    )

    if not has_price_data:
        # No verified price/technical data exists for this ticker at all (e.g. it isn't
        # a recognized symbol on the market data provider). Say so explicitly and forbid
        # inventing technical-sounding claims - without this, the model tends to write a
        # normal-looking recommendation that implies real analysis happened when it didn't.
        indicators_block = (
            "NO VERIFIED PRICE OR TECHNICAL DATA IS AVAILABLE for this ticker - it could "
            "not be found on the market data provider (it may be misspelled, delisted, or "
            "not covered - e.g. many non-US companies are only covered if they have a "
            "US-listed ADR). Do NOT describe RSI, MACD, moving averages, price trends, or "
            "any other technical detail as if it were observed - none of it exists. "
            "Explicitly state in the reasoning that no price data was found for this symbol."
        )
    else:
        indicators_block = f"""- RSI(14): {latest_indicators.get('rsi_14')}
- MACD histogram: {latest_indicators.get('macd_hist')}
- Price vs SMA(20): {latest_indicators.get('sma_20')}
- Bollinger position: close={latest_indicators.get('close')}, upper={latest_indicators.get('bollinger_upper')}, lower={latest_indicators.get('bollinger_lower')}
- Rolling volatility(20): {latest_indicators.get('volatility_20')}"""

    return f"""Ticker: {ticker}

ML signal: {ml_signal}{heuristic_note}
ML predicted next-interval return: {ml_predicted_return:.4f}
ML confidence: {ml_confidence:.2f}

Latest technical indicators:
{indicators_block}

Recent news context:
{chunks_block}

Relevant investing principles retrieved for this specific technical/market situation
(from a curated library of investing/trading books - use only the ones that genuinely
apply, per instruction 4):
{strategies_block}

Produce the buy/sell/hold recommendation JSON now."""
