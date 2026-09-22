"""Technical indicator calculations over OHLCV bars, using plain pandas (no extra TA
dependency, to keep the install light). Input: list of bar dicts with ts/open/high/low/close/volume,
oldest-first. Output: same bars enriched with indicator fields.
"""
from __future__ import annotations

import pandas as pd


def compute_indicators(bars: list[dict]) -> list[dict]:
    if not bars:
        return []

    df = pd.DataFrame(bars).sort_values("ts").reset_index(drop=True)
    close = df["close"]

    # SMA / EMA
    df["sma_20"] = close.rolling(window=20, min_periods=1).mean()
    df["ema_20"] = close.ewm(span=20, adjust=False, min_periods=1).mean()

    # RSI(14)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    df["rsi_14"] = 100 - (100 / (1 + rs))
    df["rsi_14"] = df["rsi_14"].fillna(50.0)  # neutral when undefined (e.g. no losses yet)

    # MACD (12, 26, 9)
    ema_12 = close.ewm(span=12, adjust=False, min_periods=1).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=1).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False, min_periods=1).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Bollinger Bands (20, 2 std)
    mid = close.rolling(window=20, min_periods=1).mean()
    std = close.rolling(window=20, min_periods=1).std().fillna(0)
    df["bollinger_mid"] = mid
    df["bollinger_upper"] = mid + 2 * std
    df["bollinger_lower"] = mid - 2 * std

    # Rolling volatility: stddev of returns over 20 periods
    returns = close.pct_change()
    df["volatility_20"] = returns.rolling(window=20, min_periods=1).std().fillna(0)

    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")
