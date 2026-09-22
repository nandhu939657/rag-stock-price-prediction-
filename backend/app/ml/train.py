"""Offline training script for the ML signal model. Not part of the live request path -
run manually: `python -m app.ml.train` (from backend/, with the venv active).

Trains on DAILY bars across a curated basket of liquid tickers (not one model per ticker),
so a newly tracked stock doesn't need months of its own history before getting a signal.
Note: the live pipeline applies this same model to 5-minute bars' engineered features
(returns/RSI/MACD/etc. are scale-similar across timeframes) - this is a deliberate v1
simplification. A future improvement is training a separate intraday model once enough
5-minute history has accumulated in price_history for the tracked basket.

Time-based train/validation split only - never shuffle across time (lookahead leakage).
"""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # allow `python -m app.ml.train`

from app.ingestion.indicators import compute_indicators
from app.ingestion.market_data_client import fetch_recent_bars
from app.ml.features import FEATURE_COLUMNS, build_feature_frame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = pathlib.Path(__file__).parent / "artifacts"

# Curated basket of liquid, well-known tickers for training data breadth.
TICKER_BASKET = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT",
    "UNH", "XOM", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "KO", "PEP",
    "BAC", "AVGO", "COST", "DIS", "ADBE", "CRM", "NFLX", "AMD", "INTC", "CSCO",
]

FLAT_THRESHOLD = 0.002  # +/-0.2% dead zone for the direction classifier


async def _fetch_ticker_history(ticker: str) -> pd.DataFrame | None:
    try:
        bars = await fetch_recent_bars(ticker, interval="1day", output_size=500)  # Infoway's per-call cap
    except Exception as e:  # noqa: BLE001 - any single ticker failing shouldn't kill the run
        logger.warning("Skipping %s: %s", ticker, e)
        return None
    if len(bars) < 60:
        logger.warning("Skipping %s: only %d bars returned", ticker, len(bars))
        return None
    enriched = compute_indicators(bars)
    df = pd.DataFrame(enriched)
    df["ticker"] = ticker
    return df


def _label(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["forward_return"] = df["close"].shift(-1) / df["close"] - 1
    df["direction"] = np.where(
        df["forward_return"] > FLAT_THRESHOLD, "up",
        np.where(df["forward_return"] < -FLAT_THRESHOLD, "down", "flat"),
    )
    return df


async def build_training_set() -> pd.DataFrame:
    frames = []
    for ticker in TICKER_BASKET:
        df = await _fetch_ticker_history(ticker)
        if df is None:
            continue
        df = build_feature_frame(df)
        df = _label(df)
        frames.append(df)

    if not frames:
        raise RuntimeError(
            "No training data could be fetched for any ticker in the basket. "
            "Check MARKET_DATA_API_KEY in the project's .env file."
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=FEATURE_COLUMNS + ["forward_return", "direction"])
    return combined


def time_based_split(df: pd.DataFrame, train_frac: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-ticker time-based split (sort by ts within ticker, take the first train_frac as train)."""
    train_parts, val_parts = [], []
    for _, group in df.groupby("ticker"):
        group = group.sort_values("ts")
        split_idx = int(len(group) * train_frac)
        train_parts.append(group.iloc[:split_idx])
        val_parts.append(group.iloc[split_idx:])
    return pd.concat(train_parts), pd.concat(val_parts)


def train_and_save(df: pd.DataFrame) -> None:
    import xgboost as xgb
    from sklearn.metrics import accuracy_score, mean_absolute_error

    train_df, val_df = time_based_split(df)
    x_train, x_val = train_df[FEATURE_COLUMNS], val_df[FEATURE_COLUMNS]

    classifier = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05, objective="multi:softprob", eval_metric="mlogloss"
    )
    classifier.fit(x_train, train_df["direction"])
    val_pred = classifier.predict(x_val)
    acc = accuracy_score(val_df["direction"], val_pred)
    baseline_acc = val_df["direction"].value_counts(normalize=True).max()
    logger.info("Classifier validation accuracy: %.4f (naive baseline: %.4f)", acc, baseline_acc)

    regressor = xgb.XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, objective="reg:squarederror")
    regressor.fit(x_train, train_df["forward_return"])
    val_pred_ret = regressor.predict(x_val)
    mae = mean_absolute_error(val_df["forward_return"], val_pred_ret)
    logger.info("Regressor validation MAE: %.5f", mae)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    classifier.save_model(str(ARTIFACTS_DIR / "xgb_direction_v1.json"))
    regressor.save_model(str(ARTIFACTS_DIR / "xgb_return_v1.json"))
    (ARTIFACTS_DIR / "feature_columns.json").write_text(json.dumps({"feature_columns": FEATURE_COLUMNS}, indent=2))
    logger.info("Saved model artifacts to %s", ARTIFACTS_DIR)


async def main() -> None:
    logger.info("Building training set from %d tickers (daily bars)...", len(TICKER_BASKET))
    df = await build_training_set()
    logger.info("Training set: %d rows across %d tickers", len(df), df["ticker"].nunique())
    train_and_save(df)


if __name__ == "__main__":
    asyncio.run(main())
