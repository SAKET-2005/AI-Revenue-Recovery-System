"""
ML model trainer for recovery probability prediction.

Trains an XGBoost classifier with proper train/val/test split,
evaluates metrics, and saves artifacts.
"""

import json
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    accuracy_score, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import joblib
from typing import Tuple, Dict, Any, List


CATEGORICAL_FEATURES = ["payment_method", "failure_code", "device_type", "merchant_category"]
NUMERICAL_FEATURES = [
    "amount", "retry_count", "checkout_duration",
    "cart_value", "is_returning_customer", "transaction_frequency"
]

ML_ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml_artifacts")


class RecoveryModelTrainer:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.model = None
        self.metrics: Dict[str, Any] = {}
        self.feature_names: List[str] = []

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features and return feature matrix."""
        df = df.copy()
        for col in CATEGORICAL_FEATURES:
            if col not in self.label_encoders:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders[col]
                # Handle unseen categories
                df[col] = df[col].astype(str).map(
                    lambda x, le=le: le.transform([x])[0] if x in le.classes_ else -1
                )

        self.feature_names = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
        return df[self.feature_names]

    def train(self, feature_dicts: List[Dict], labels: List[int]) -> Dict[str, Any]:
        """Train the model with 70/15/15 split."""
        df = pd.DataFrame(feature_dicts)
        y = np.array(labels)

        # Prepare features
        X = self._prepare_features(df)

        # Split: 70% train, 15% val, 15% test
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.30, random_state=self.seed, stratify=y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, random_state=self.seed, stratify=y_temp
        )

        # Train XGBoost
        self.model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=self.seed,
            eval_metric="logloss",
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        # Evaluate on TEST set
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba >= 0.5).astype(int)

        cm = confusion_matrix(y_test, y_pred).tolist()

        self.metrics = {
            "model_version": "xgb_v1",
            "roc_auc": round(float(roc_auc_score(y_test, y_pred_proba)), 4),
            "precision": round(float(precision_score(y_test, y_pred)), 4),
            "recall": round(float(recall_score(y_test, y_pred)), 4),
            "f1": round(float(f1_score(y_test, y_pred)), 4),
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "confusion_matrix": cm,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "feature_importances": {
                name: round(float(imp), 4)
                for name, imp in zip(self.feature_names, self.model.feature_importances_)
            },
        }

        return self.metrics

    def save(self, path: str = None):
        """Save model and artifacts."""
        if path is None:
            path = ML_ARTIFACTS_DIR
        os.makedirs(path, exist_ok=True)

        joblib.dump(self.model, os.path.join(path, "recovery_model.joblib"))
        joblib.dump(self.label_encoders, os.path.join(path, "label_encoders.joblib"))
        joblib.dump(self.feature_names, os.path.join(path, "feature_names.joblib"))

        with open(os.path.join(path, "metrics.json"), "w") as f:
            json.dump(self.metrics, f, indent=2)

    @staticmethod
    def load(path: str = None) -> Tuple:
        """Load saved model artifacts."""
        if path is None:
            path = ML_ARTIFACTS_DIR
        model = joblib.load(os.path.join(path, "recovery_model.joblib"))
        encoders = joblib.load(os.path.join(path, "label_encoders.joblib"))
        feature_names = joblib.load(os.path.join(path, "feature_names.joblib"))
        return model, encoders, feature_names
