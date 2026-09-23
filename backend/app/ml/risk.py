"""Risk assessment for a recommendation - deliberately a set of concrete, explainable
factors plus a plain-language summary, rather than a single opaque score, for the same
reason the ML confidence was fixed to stop returning a flat constant: a risk "number"
or a bare label with nothing behind it isn't trustworthy. Computed entirely from real
values already on hand (volatility, ML confidence, data availability) - never invented
by the LLM, so it can't drift or be inconsistent between two calls with the same
underlying situation.
"""
from __future__ import annotations

from typing import Literal

RiskLevel = Literal["low", "medium", "high"]

# Volatility here is the 5-minute-bar return stdev (see indicators.py's volatility_20),
# not daily volatility - these thresholds are calibrated to that scale, based on the
# range actually observed across real tickers during development (roughly 0.0005-0.002
# for calm large-caps, higher for volatile names).
_VOL_MEDIUM = 0.0008
_VOL_HIGH = 0.002


class RiskAssessment:
    def __init__(self, level: RiskLevel, summary: str, factors: list[str], score: int):
        self.level = level
        self.summary = summary  # one-sentence plain-language explanation of the level
        self.factors = factors  # the individual contributing reasons, each with real numbers
        self.score = score  # 0-100, for sorting/display only - the factors are what matter

    def to_dict(self) -> dict:
        return {"risk_level": self.level, "risk_summary": self.summary, "risk_factors": self.factors, "risk_score": self.score}


def assess_risk(
    latest_indicators: dict,
    ml_confidence: float,
    ml_is_heuristic: bool,
    has_price_data: bool,
) -> RiskAssessment:
    if not has_price_data:
        return RiskAssessment(
            level="high",
            summary="Rated high risk because there is no verified price data for this symbol at all - any call here has no real technical basis.",
            factors=["No verified price data was found for this symbol - there is no real technical basis for this call at all."],
            score=100,
        )

    factors: list[str] = []
    drivers: list[str] = []  # short phrases used to build the one-sentence summary
    score = 0

    volatility = latest_indicators.get("volatility_20")
    if volatility is not None:
        if volatility >= _VOL_HIGH:
            factors.append(f"High recent volatility ({volatility * 100:.2f}% per bar) - price is swinging sharply, so any position can move against you quickly.")
            drivers.append("high recent volatility")
            score += 40
        elif volatility >= _VOL_MEDIUM:
            factors.append(f"Moderate recent volatility ({volatility * 100:.2f}% per bar).")
            score += 20
        else:
            factors.append(f"Low recent volatility ({volatility * 100:.2f}% per bar) - price has been relatively calm, which lowers the risk contribution.")
            score += 5

    if ml_confidence < 0.3:
        factors.append(f"Low model confidence ({ml_confidence * 100:.0f}%) - the underlying signal itself is uncertain, which weakens the basis for this call.")
        drivers.append("low model confidence")
        score += 35
    elif ml_confidence < 0.5:
        factors.append(f"Moderate model confidence ({ml_confidence * 100:.0f}%) - the signal leans one way but isn't strongly one-sided.")
        score += 15
    else:
        factors.append(f"Reasonably high model confidence ({ml_confidence * 100:.0f}%), which lowers the risk contribution from signal uncertainty.")
        score += 5

    if ml_is_heuristic:
        factors.append(
            "The signal comes from a simple RSI/MACD heuristic, not the trained model (usually because this "
            "stock doesn't have enough price history yet) - treat it as cruder than a normal call."
        )
        drivers.append("using the cruder fallback heuristic instead of the trained model")
        score += 20

    bollinger_position = latest_indicators.get("bollinger_position")
    if bollinger_position is not None and (bollinger_position > 0.95 or bollinger_position < 0.05):
        factors.append("Price is at a technical extreme (edge of its Bollinger Bands), which can mean sharper near-term moves either way.")
        drivers.append("price sitting at a technical extreme")
        score += 10

    score = min(score, 100)
    if score >= 55:
        level: RiskLevel = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    if not factors:
        factors.append("No elevated risk factors identified from the available technical data.")

    if drivers:
        summary = f"Rated {level} risk, mainly driven by {', '.join(drivers)}."
    elif level == "low":
        summary = "Rated low risk - volatility and model confidence are both in a comfortable range for this call."
    else:
        summary = f"Rated {level} risk based on a combination of moderate factors below, none individually severe."

    return RiskAssessment(level=level, summary=summary, factors=factors, score=score)
