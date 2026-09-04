"""
ML prediction service for recovery probability.

Loads trained model and provides inference.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Optional, Any, List

ML_ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml_artifacts")

CATEGORICAL_FEATURES = ["payment_method", "failure_code", "device_type", "merchant_category"]
NUMERICAL_FEATURES = [
    "amount", "retry_count", "checkout_duration",
    "cart_value", "is_returning_customer", "transaction_frequency"
]


class RecoveryPredictor:
    """Predicts recovery probability for failed transactions."""

    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_names: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self._loaded = False

    def load(self, path: str = None) -> bool:
        """Load model artifacts. Returns True if successful."""
        if path is None:
            path = ML_ARTIFACTS_DIR
        try:
            self.model = joblib.load(os.path.join(path, "recovery_model.joblib"))
            self.label_encoders = joblib.load(os.path.join(path, "label_encoders.joblib"))
            self.feature_names = joblib.load(os.path.join(path, "feature_names.joblib"))
            metrics_path = os.path.join(path, "metrics.json")
            if os.path.exists(metrics_path):
                with open(metrics_path) as f:
                    self.metrics = json.load(f)
            self._loaded = True
            return True
        except Exception as e:
            print(f"[ML] Failed to load model: {e}")
            self._loaded = False
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, features: Dict) -> Dict:
        """
        Predict recovery probability for a single transaction.

        Args:
            features: dict with keys matching training features

        Returns:
            {recovery_probability, confidence, feature_importances}
        """
        if not self._loaded:
            # Fallback heuristic
            return self._heuristic_predict(features)

        try:
            df = pd.DataFrame([features])

            # Encode categoricals
            for col in CATEGORICAL_FEATURES:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    val = str(df[col].iloc[0])
                    if val in le.classes_:
                        df[col] = le.transform([val])
                    else:
                        df[col] = -1
                else:
                    df[col] = 0

            X = df[self.feature_names]
            proba = self.model.predict_proba(X)[0, 1]

            # Feature importances for this prediction
            importances = {}
            if hasattr(self.model, "feature_importances_"):
                for name, imp in zip(self.feature_names, self.model.feature_importances_):
                    importances[name] = round(float(imp), 4)

            return {
                "recovery_probability": round(float(proba), 4),
                "confidence": round(float(max(proba, 1 - proba)), 4),
                "feature_importances": importances,
                "model_version": "xgb_v1",
            }
        except Exception as e:
            print(f"[ML] Prediction error: {e}")
            return self._heuristic_predict(features)

    def _heuristic_predict(self, features: Dict) -> Dict:
        """Deterministic fallback when model is unavailable."""
        from app.utils.data_generator import FAILURE_RECOVERY_BASE

        failure_code = features.get("failure_code", "unknown")
        base = FAILURE_RECOVERY_BASE.get(failure_code, 0.25)

        # Adjustments
        if features.get("is_returning_customer"):
            base += 0.08
        if features.get("retry_count", 0) >= 2:
            base -= 0.20
        if features.get("amount", 0) > 10000:
            base -= 0.05
        if features.get("amount", 0) > 50000:
            base -= 0.10

        prob = max(0.02, min(0.98, base))

        return {
            "recovery_probability": round(prob, 4),
            "confidence": round(max(prob, 1 - prob), 4),
            "feature_importances": {"failure_code": 0.35, "amount": 0.20, "is_returning_customer": 0.15},
            "model_version": "heuristic_fallback",
        }

    def get_metrics(self) -> Dict:
        """Return stored model metrics."""
        return self.metrics


# Singleton
predictor = RecoveryPredictor()
