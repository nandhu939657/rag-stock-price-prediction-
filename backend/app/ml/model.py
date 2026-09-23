"""ML signal model serving. Loads trained XGBoost artifacts once at startup (singleton).

If no trained artifact exists yet (train.py hasn't been run), falls back to a simple
RSI/MACD threshold heuristic so the pipeline still produces a (low-confidence) signal
instead of failing outright - this also covers the cold-start case for a brand-new stock.
"""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Literal

from app.ml.features import DIRECTION_LABELS

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = pathlib.Path(__file__).parent / "artifacts"
CLASSIFIER_PATH = ARTIFACTS_DIR / "xgb_direction_v1.json"
REGRESSOR_PATH = ARTIFACTS_DIR / "xgb_return_v1.json"
FEATURE_MANIFEST_PATH = ARTIFACTS_DIR / "feature_columns.json"

Signal = Literal["up", "down", "flat"]


class MLPrediction:
    def __init__(self, signal: Signal, predicted_return: float, confidence: float, is_heuristic: bool):
        self.signal = signal
        self.predicted_return = predicted_return
        self.confidence = confidence
        self.is_heuristic = is_heuristic

    def to_dict(self) -> dict:
        return {
            "ml_signal": self.signal,
            "ml_predicted_return": self.predicted_return,
            "ml_confidence": self.confidence,
            "ml_is_heuristic": self.is_heuristic,
        }


class ModelService:
    _instance: "ModelService | None" = None

    def __init__(self):
        self.classifier = None
        self.regressor = None
        self.feature_columns: list[str] | None = None
        self._try_load()

    @classmethod
    def instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _try_load(self) -> None:
        if not (CLASSIFIER_PATH.exists() and REGRESSOR_PATH.exists() and FEATURE_MANIFEST_PATH.exists()):
            logger.warning(
                "No trained ML artifacts found in %s. Run `python -m app.ml.train` to train one. "
                "Falling back to a heuristic signal until then.",
                ARTIFACTS_DIR,
            )
            return

        import xgboost as xgb

        self.classifier = xgb.XGBClassifier()
        self.classifier.load_model(str(CLASSIFIER_PATH))
        self.regressor = xgb.XGBRegressor()
        self.regressor.load_model(str(REGRESSOR_PATH))
        self.feature_columns = json.loads(FEATURE_MANIFEST_PATH.read_text())["feature_columns"]
        logger.info("Loaded ML model artifacts from %s", ARTIFACTS_DIR)

    @property
    def is_trained(self) -> bool:
        return self.classifier is not None and self.regressor is not None

    def predict(self, feature_vector: dict[str, float] | None) -> MLPrediction:
        if feature_vector is None:
            return MLPrediction(signal="flat", predicted_return=0.0, confidence=0.0, is_heuristic=True)

        if self.is_trained:
            return self._predict_ml(feature_vector)
        return self._predict_heuristic(feature_vector)

    def _predict_ml(self, feature_vector: dict[str, float]) -> MLPrediction:
        import numpy as np

        assert self.feature_columns is not None
        x = np.array([[feature_vector[c] for c in self.feature_columns]])

        # The classifier was trained on integer-encoded labels (0=down, 1=flat, 2=up -
        # see DIRECTION_LABELS in app/ml/features.py and how train.py encodes before
        # fit()), so predict_proba's column order matches DIRECTION_LABELS directly -
        # decode through that same fixed list rather than self.classifier.classes_
        # (which would just be [0, 1, 2], not the string signal names).
        proba = self.classifier.predict_proba(x)[0]
        pred_idx = int(np.argmax(proba))
        signal: Signal = DIRECTION_LABELS[pred_idx]
        confidence = float(proba[pred_idx])

        predicted_return = float(self.regressor.predict(x)[0])

        return MLPrediction(signal=signal, predicted_return=predicted_return, confidence=confidence, is_heuristic=False)

    @staticmethod
    def _predict_heuristic(feature_vector: dict[str, float]) -> MLPrediction:
        """RSI/MACD/Bollinger threshold fallback - used until train.py has produced a
        real model, or when a stock has too little history for the trained model's
        feature set. Deliberately NOT a flat constant: confidence and predicted_return
        are both derived from how extreme and how aligned the underlying indicators
        actually are, so two different technical pictures produce two different
        numbers instead of always reporting the same placeholder value regardless of
        input. Still capped well below what a genuinely trained model could claim,
        since three threshold rules are a much cruder signal than a trained model."""
        rsi = feature_vector.get("rsi_14", 50.0)
        macd_hist = feature_vector.get("macd_hist", 0.0)
        bollinger_position = feature_vector.get("bollinger_position", 0.5)

        rsi_direction = 1 if rsi < 30 else (-1 if rsi > 70 else 0)
        rsi_strength = min(abs(rsi - 50) / 50, 1.0)  # 0 at neutral (50), 1 at the extremes (0/100)

        macd_direction = 1 if macd_hist > 0 else (-1 if macd_hist < 0 else 0)

        boll_direction = 1 if bollinger_position < 0.15 else (-1 if bollinger_position > 0.85 else 0)
        boll_strength = min(abs(bollinger_position - 0.5) / 0.5, 1.0)  # 0 at mid-band, 1 at either edge

        votes = [v for v in (rsi_direction, macd_direction, boll_direction) if v != 0]
        net = sum(votes)

        if net > 0:
            signal: Signal = "up"
        elif net < 0:
            signal = "down"
        else:
            signal = "flat"

        agreement = abs(net) / 3  # fraction of the 3 signals that agree with the winning direction
        avg_strength = (rsi_strength + boll_strength) / 2
        confidence = round(min(0.15 + 0.25 * agreement + 0.15 * avg_strength, 0.55), 2)

        # Rough, sign-consistent return estimate from how far RSI sits from neutral -
        # not a real regression, just enough to avoid reporting a hard 0.0 every time.
        predicted_return = round(((50 - rsi) / 50) * 0.01, 4)

        return MLPrediction(signal=signal, predicted_return=predicted_return, confidence=confidence, is_heuristic=True)


def get_model_service() -> ModelService:
    return ModelService.instance()
