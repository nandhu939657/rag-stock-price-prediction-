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

        proba = self.classifier.predict_proba(x)[0]  # order: classes_ e.g. [down, flat, up]
        classes = list(self.classifier.classes_)
        pred_idx = int(np.argmax(proba))
        signal: Signal = classes[pred_idx]
        confidence = float(proba[pred_idx])

        predicted_return = float(self.regressor.predict(x)[0])

        return MLPrediction(signal=signal, predicted_return=predicted_return, confidence=confidence, is_heuristic=False)

    @staticmethod
    def _predict_heuristic(feature_vector: dict[str, float]) -> MLPrediction:
        """RSI/MACD threshold fallback - used until train.py has produced a real model,
        or when a stock has too little history for the trained model's feature set."""
        rsi = feature_vector.get("rsi_14", 50.0)
        macd_hist = feature_vector.get("macd_hist", 0.0)

        score = 0
        if rsi < 30:
            score += 1
        elif rsi > 70:
            score -= 1
        if macd_hist > 0:
            score += 1
        elif macd_hist < 0:
            score -= 1

        if score >= 1:
            signal: Signal = "up"
        elif score <= -1:
            signal = "down"
        else:
            signal = "flat"

        return MLPrediction(signal=signal, predicted_return=0.0, confidence=0.25, is_heuristic=True)


def get_model_service() -> ModelService:
    return ModelService.instance()
