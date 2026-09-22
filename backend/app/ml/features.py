"""Feature engineering for the ML signal model. Shared by offline training (train.py)
and live inference (model.py) so features never drift between the two.

Input: a DataFrame of price bars (oldest-first) already enriched with indicators from
app.ingestion.indicators.compute_indicators (sma_20, ema_20, rsi_14, macd*, bollinger*,
volatility_20).
"""
from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = [
    "return_1",
    "return_5",
    "return_10",
    "return_20",
    "price_to_sma20",
    "price_to_ema20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bollinger_position",
    "volatility_20",
    "volume_ratio",
]

MIN_BARS_FOR_FEATURES = 21  # need at least return_20 to be meaningful


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Adds FEATURE_COLUMNS to df (already sorted oldest-first, indicators present)."""
    df = df.copy()
    close = df["close"]

    df["return_1"] = close.pct_change(1)
    df["return_5"] = close.pct_change(5)
    df["return_10"] = close.pct_change(10)
    df["return_20"] = close.pct_change(20)

    df["price_to_sma20"] = (close / df["sma_20"].replace(0, pd.NA)) - 1
    df["price_to_ema20"] = (close / df["ema_20"].replace(0, pd.NA)) - 1

    band_width = (df["bollinger_upper"] - df["bollinger_lower"]).replace(0, pd.NA)
    df["bollinger_position"] = ((close - df["bollinger_lower"]) / band_width).clip(0, 1)

    avg_volume = df["volume"].rolling(window=20, min_periods=1).mean().replace(0, pd.NA)
    df["volume_ratio"] = df["volume"] / avg_volume

    return df


def latest_feature_vector(df_with_features: pd.DataFrame) -> dict[str, float] | None:
    """Extract the feature vector for the most recent bar, or None if too little history."""
    if len(df_with_features) < MIN_BARS_FOR_FEATURES:
        return None
    row = df_with_features.iloc[-1]
    vector = {col: row.get(col) for col in FEATURE_COLUMNS}
    if any(v is None or pd.isna(v) for v in vector.values()):
        return None
    return {k: float(v) for k, v in vector.items()}
