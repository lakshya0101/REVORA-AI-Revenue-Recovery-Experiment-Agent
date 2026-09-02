from collections import Counter
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.services.dataset_service import dataset_service

logger = logging.getLogger(__name__)

# Core model features (Strictly excludes all ground truth columns)
NUMERICAL_FEATURES = [
    "amount",
    "previous_successful_payments",
    "previous_failed_payments",
    "previous_recovery_attempts",
    "historical_recovery_rate",
    "customer_lifetime_value",
    "time_since_failure_minutes",
]

CATEGORICAL_FEATURES = [
    "payment_status",
    "failure_reason",
    "customer_type",
    "payment_method",
    "checkout_abandoned",
    "order_value_segment",
]

FEATURE_COLUMNS = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
TARGET_STRATEGY_COL = "ground_truth_best_strategy"
TARGET_PROB_COL = "ground_truth_recovery_probability"


def derive_reason_codes(data: Dict[str, Any], recommended_strategy: str, recovery_prob: float) -> List[str]:
    """Deterministic, auditable business rule reason codes derived from transaction context."""
    reasons: List[str] = []
    failure_reason = str(data.get("failure_reason", "")).upper()
    cust_type = str(data.get("customer_type", "")).upper()
    hist_rate = float(data.get("historical_recovery_rate", 0.0))
    time_min = float(data.get("time_since_failure_minutes", 0.0))
    checkout_abandoned = bool(data.get("checkout_abandoned", False))
    amount = float(data.get("amount", 0.0))

    if failure_reason in ["BANK_SERVER_DOWN", "NETWORK_TIMEOUT", "GATEWAY_REJECTED"]:
        reasons.append("TEMPORARY_SYSTEM_FAILURE")
    elif failure_reason in ["INCORRECT_OTP", "CARD_AUTHENTICATION_FAILED"]:
        reasons.append("USER_AUTHENTICATION_DROPOFF")
    elif failure_reason in ["INSUFFICIENT_FUNDS", "TRANSACTION_LIMIT_EXCEEDED"]:
        reasons.append("FINANCIAL_LIMIT_CONSTRAINT")
    elif failure_reason in ["EXPIRED_CARD", "UPI_APP_UNRESPONSIVE"]:
        reasons.append("METHOD_SPECIFIC_ISSUE")

    if checkout_abandoned:
        reasons.append("CHECKOUT_ABANDONMENT_INTENT")

    if cust_type in ["VIP", "ENTERPRISE"] or hist_rate >= 0.6:
        reasons.append("STRONG_CUSTOMER_HISTORY")
    elif cust_type == "FIRST_TIME":
        reasons.append("FIRST_TIME_BUYER")
    elif hist_rate < 0.2 and float(data.get("previous_failed_payments", 0)) > 3:
        reasons.append("CHRONIC_FAILURE_PROFILE")

    if time_min < 30:
        reasons.append("IMMEDIATE_RECOVERY_WINDOW")
    elif time_min > 1440:
        reasons.append("ELAPSED_CONVERSION_WINDOW")

    if recovery_prob >= 0.70:
        reasons.append("HIGH_RECOVERY_POTENTIAL")
    elif recovery_prob < 0.30:
        reasons.append("LOW_RECOVERY_PROBABILITY")

    if amount >= 25000:
        reasons.append("HIGH_VALUE_TRANSACTION_PRIORITY")

    if not reasons:
        reasons.append("STANDARD_RECOVERY_PROFILE")

    return reasons[:4]


class RecoveryDecisionEngine:
    """Machine Learning decision engine for automated revenue recovery strategy and recovery probability prediction."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.strategy_pipeline: Optional[Pipeline] = None
        self.probability_pipeline: Optional[Pipeline] = None
        self.evaluation_results: Dict[str, Any] = {}
        self.baseline_strategy: str = "PAYMENT_LINK"
        self._is_trained: bool = False

    def _build_preprocessor(self) -> ColumnTransformer:
        return ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), NUMERICAL_FEATURES),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ]
        )

    def train_and_evaluate(self) -> Dict[str, Any]:
        """Train models on 80% split and perform rigorous evaluation on 20% held-out test set."""
        raw_cases = dataset_service.load_dataset()
        if not raw_cases:
            raise ValueError("Dataset is empty. Cannot train recovery decision engine.")

        df = pd.DataFrame(raw_cases)

        # Prepare X and target variables
        X = df[FEATURE_COLUMNS].copy()
        y_strategy = df[TARGET_STRATEGY_COL].copy()
        y_prob = df[TARGET_PROB_COL].copy()

        # Hold-out split (80% train, 20% test)
        (
            X_train,
            X_test,
            y_strat_train,
            y_strat_test,
            y_prob_train,
            y_prob_test,
            indices_train,
            indices_test,
        ) = train_test_split(
            X,
            y_strategy,
            y_prob,
            df.index,
            test_size=0.20,
            random_state=self.random_state,
            stratify=y_strategy,
        )

        # Naive Baseline Strategy: Most frequent strategy in training data
        train_counts = Counter(y_strat_train)
        self.baseline_strategy = train_counts.most_common(1)[0][0]
        baseline_preds = [self.baseline_strategy] * len(y_strat_test)
        baseline_accuracy = float(accuracy_score(y_strat_test, baseline_preds))

        # 1. Strategy Classifier
        strat_preprocessor = self._build_preprocessor()
        self.strategy_pipeline = Pipeline(
            steps=[
                ("preprocessor", strat_preprocessor),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=120,
                        max_depth=12,
                        min_samples_split=4,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )
        self.strategy_pipeline.fit(X_train, y_strat_train)

        # 2. Recovery Probability Regressor
        prob_preprocessor = self._build_preprocessor()
        self.probability_pipeline = Pipeline(
            steps=[
                ("preprocessor", prob_preprocessor),
                (
                    "regressor",
                    RandomForestRegressor(
                        n_estimators=100,
                        max_depth=10,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )
        self.probability_pipeline.fit(X_train, y_prob_train)
        self._is_trained = True

        # Test set evaluation
        test_strat_preds = self.strategy_pipeline.predict(X_test)
        test_prob_preds = np.clip(self.probability_pipeline.predict(X_test), 0.0, 1.0)

        # Classification Metrics
        unique_labels = sorted(list(set(y_strategy)))
        strat_acc = float(accuracy_score(y_strat_test, test_strat_preds))
        strat_prec = float(precision_score(y_strat_test, test_strat_preds, average="macro", zero_division=0))
        strat_rec = float(recall_score(y_strat_test, test_strat_preds, average="macro", zero_division=0))
        strat_f1 = float(f1_score(y_strat_test, test_strat_preds, average="macro", zero_division=0))
        cm = confusion_matrix(y_strat_test, test_strat_preds, labels=unique_labels).tolist()

        # Regression Metrics
        prob_mae = float(mean_absolute_error(y_prob_test, test_prob_preds))
        prob_rmse = float(np.sqrt(mean_squared_error(y_prob_test, test_prob_preds)))

        # Revenue Metrics on Held-out Test Set
        test_df = df.loc[indices_test].copy()
        test_revenue_at_risk = float(test_df["amount"].sum())
        actual_recovered_revenue = float(test_df["ground_truth_recovered_amount"].sum())
        predicted_expected_recovery = float((test_df["amount"].values * test_prob_preds).sum())
        ground_truth_recovered_cases = int(test_df["ground_truth_recovered"].sum())
        ground_truth_recovery_rate = float(ground_truth_recovered_cases / len(test_df))

        improvement_over_baseline = round(strat_acc - baseline_accuracy, 4)

        self.evaluation_results = {
            "model": {
                "algorithm": "RandomForest (Classifier & Regressor)",
                "train_size": len(X_train),
                "test_size": len(X_test),
                "accuracy": round(strat_acc, 4),
                "precision_macro": round(strat_prec, 4),
                "recall_macro": round(strat_rec, 4),
                "f1_macro": round(strat_f1, 4),
                "confusion_matrix": cm,
                "labels": unique_labels,
            },
            "baseline": {
                "strategy": self.baseline_strategy,
                "accuracy": round(baseline_accuracy, 4),
            },
            "improvement": improvement_over_baseline,
            "recovery_probability": {
                "mae": round(prob_mae, 4),
                "rmse": round(prob_rmse, 4),
            },
            "revenue": {
                "test_revenue_at_risk": round(test_revenue_at_risk, 2),
                "predicted_expected_recovery": round(predicted_expected_recovery, 2),
                "actual_recovered_revenue": round(actual_recovered_revenue, 2),
                "ground_truth_recovery_rate": round(ground_truth_recovery_rate, 4),
            },
        }

        logger.info(
            "Model trained successfully. Test Accuracy: %.2f%% (Baseline: %.2f%%)",
            strat_acc * 100,
            baseline_accuracy * 100,
        )
        return self.evaluation_results

    def get_evaluation(self) -> Dict[str, Any]:
        """Return the pre-computed evaluation results on the held-out test set."""
        if not self._is_trained or not self.evaluation_results:
            return self.train_and_evaluate()
        return self.evaluation_results

    def predict(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a recovery strategy decision for an input transaction."""
        if not self._is_trained:
            self.train_and_evaluate()

        # Sanitize input: extract only feature columns
        feat_dict = {}
        for col in FEATURE_COLUMNS:
            val = transaction_data.get(col)
            if val is None:
                # Provide reasonable default if missing
                val = 0.0 if col in NUMERICAL_FEATURES else "UNKNOWN"
            if col == "checkout_abandoned":
                val = bool(val)
            elif col in NUMERICAL_FEATURES:
                val = float(val)
            else:
                val = str(val)
            feat_dict[col] = [val]

        df_input = pd.DataFrame(feat_dict)

        # Strategy & Confidence Prediction
        pred_strategy = self.strategy_pipeline.predict(df_input)[0]
        class_probs = self.strategy_pipeline.predict_proba(df_input)[0]
        strategy_confidence = float(np.max(class_probs))

        # Recovery Probability Prediction
        pred_prob_raw = float(self.probability_pipeline.predict(df_input)[0])
        pred_prob = float(np.clip(pred_prob_raw, 0.01, 0.99))

        amount = float(transaction_data.get("amount", 0.0))
        expected_recovery_val = round(amount * pred_prob, 2)
        transaction_id = str(transaction_data.get("transaction_id", "txn_unknown"))

        reason_codes = derive_reason_codes(transaction_data, pred_strategy, pred_prob)

        return {
            "transaction_id": transaction_id,
            "recommended_strategy": str(pred_strategy),
            "strategy_confidence": round(strategy_confidence, 4),
            "predicted_recovery_probability": round(pred_prob, 4),
            "expected_recovery_value": expected_recovery_val,
            "reason_codes": reason_codes,
        }


recovery_engine = RecoveryDecisionEngine()
