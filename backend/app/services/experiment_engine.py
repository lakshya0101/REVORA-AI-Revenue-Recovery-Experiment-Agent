from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional
import uuid

import numpy as np

from app.agents.recovery_decision_engine import FEATURE_COLUMNS, derive_reason_codes, recovery_engine
from app.services.dataset_service import dataset_service
from app.services.recovery_policy import default_policy

STRATEGIES = ["RETRY", "PAYMENT_LINK", "ALTERNATE_FLOW", "NO_ACTION"]


def simulate_counterfactual_strategy_probabilities(transaction: Dict[str, Any], seed: Optional[int] = None) -> Dict[str, float]:
    """Simulate realistic counterfactual recovery probabilities for each of the 4 strategies.

    IMPORTANT: This simulation is used exclusively for experiment evaluation and is NOT used as an ML feature.
    """
    txn_id = str(transaction.get("transaction_id", "txn"))
    # Stable deterministic hashing if no seed is supplied
    if seed is None:
        int_seed = int(hashlib.md5(txn_id.encode("utf-8")).hexdigest()[:8], 16)
    else:
        int_seed = seed
    rng = random.Random(int_seed)

    failure_reason = str(transaction.get("failure_reason", "")).upper()
    payment_method = str(transaction.get("payment_method", "")).upper()
    customer_type = str(transaction.get("customer_type", "")).upper()
    hist_rate = float(transaction.get("historical_recovery_rate", 0.5))
    time_min = float(transaction.get("time_since_failure_minutes", 15))
    checkout_abandoned = bool(transaction.get("checkout_abandoned", False))
    prev_failed = int(transaction.get("previous_failed_payments", 0))

    # Baseline probabilities per strategy
    prob_retry = 0.35
    prob_payment_link = 0.40
    prob_alternate_flow = 0.38
    prob_no_action = 0.05

    # Contextual affinities
    if failure_reason in ["BANK_SERVER_DOWN", "NETWORK_TIMEOUT", "GATEWAY_REJECTED"]:
        prob_retry += 0.35
        prob_payment_link += 0.10
        prob_alternate_flow += 0.05
    elif failure_reason in ["CHECKOUT_DROPOFF", "INCORRECT_OTP"] or checkout_abandoned:
        prob_payment_link += 0.38
        prob_retry -= 0.15
        prob_alternate_flow += 0.10
    elif failure_reason in ["EXPIRED_CARD", "UPI_APP_UNRESPONSIVE", "CARD_AUTHENTICATION_FAILED"]:
        prob_alternate_flow += 0.35
        prob_payment_link += 0.15
        prob_retry -= 0.15
    elif failure_reason in ["INSUFFICIENT_FUNDS", "TRANSACTION_LIMIT_EXCEEDED"]:
        if customer_type in ["ENTERPRISE", "VIP", "RETURNING"] and hist_rate >= 0.4:
            prob_payment_link += 0.25
            prob_alternate_flow += 0.20
        else:
            prob_no_action = 0.08
            prob_retry -= 0.20
            prob_payment_link -= 0.15

    # Customer loyalty effect
    if customer_type in ["VIP", "ENTERPRISE"]:
        prob_retry += 0.10
        prob_payment_link += 0.12
        prob_alternate_flow += 0.10
    elif customer_type == "RETURNING":
        prob_payment_link += 0.06 * (hist_rate - 0.5)

    # Time decay
    if time_min > 1440:  # > 24 hours
        prob_retry -= 0.20
        prob_payment_link -= 0.05
    elif time_min < 30:
        prob_retry += 0.10

    # Repeat failure penalty
    if prev_failed >= 4:
        prob_retry -= 0.15
        prob_alternate_flow -= 0.10

    # Controlled noise
    res = {
        "RETRY": float(np.clip(prob_retry + rng.uniform(-0.06, 0.06), 0.02, 0.95)),
        "PAYMENT_LINK": float(np.clip(prob_payment_link + rng.uniform(-0.06, 0.06), 0.02, 0.95)),
        "ALTERNATE_FLOW": float(np.clip(prob_alternate_flow + rng.uniform(-0.06, 0.06), 0.02, 0.95)),
        "NO_ACTION": float(np.clip(prob_no_action + rng.uniform(-0.02, 0.02), 0.01, 0.12)),
    }
    return {k: round(v, 4) for k, v in res.items()}


class ExperimentStore:
    """Lightweight in-memory and local JSON persistence for experiment history."""

    def __init__(self) -> None:
        self.experiments: Dict[str, Dict[str, Any]] = {}

    def save_experiment(self, experiment_id: str, data: Dict[str, Any]) -> None:
        self.experiments[experiment_id] = data

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        return self.experiments.get(experiment_id)

    def list_experiments(self) -> List[Dict[str, Any]]:
        return sorted(
            list(self.experiments.values()),
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )


experiment_store = ExperimentStore()


class ExperimentEngine:
    """Core experiment engine comparing Revora ML-selected strategies against naive baseline."""

    def __init__(self) -> None:
        self.policy = default_policy

    def evaluate_strategy_options(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all 4 recovery strategies for a transaction payload."""
        amount = float(transaction.get("amount", 0.0))
        txn_id = str(transaction.get("transaction_id", "txn_custom"))

        # 1. Simulate counterfactual probabilities
        strat_probs = simulate_counterfactual_strategy_probabilities(transaction)

        strategies_eval = {}
        for s in STRATEGIES:
            prob = strat_probs[s]
            expected_val = round(amount * prob, 2)
            strategies_eval[s] = {
                "recovery_probability": prob,
                "expected_recovery_value": expected_val,
            }

        # 2. ML Prediction (Isolate from ground truth / counterfactuals)
        safe_txn = {k: v for k, v in transaction.items() if not k.startswith("ground_truth_")}
        ml_decision = recovery_engine.predict(safe_txn)
        raw_recommended_strategy = ml_decision["recommended_strategy"]
        raw_prob = ml_decision["predicted_recovery_probability"]

        # 3. Apply Merchant Policy Guardrails
        final_strategy, policy_result, blocking_reasons = self.policy.evaluate_guardrails(
            safe_txn, raw_recommended_strategy, raw_prob
        )

        reason_codes = list(ml_decision["reason_codes"])
        if blocking_reasons:
            reason_codes.extend(blocking_reasons)

        # Audit Event Generation
        audit_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": txn_id,
            "selected_strategy": final_strategy,
            "raw_recommended_strategy": raw_recommended_strategy,
            "confidence": ml_decision["strategy_confidence"],
            "expected_recovery_value": strategies_eval[final_strategy]["expected_recovery_value"],
            "policy_result": policy_result,
            "reason_codes": reason_codes,
        }

        return {
            "transaction_id": txn_id,
            "strategies": strategies_eval,
            "recommended_strategy": final_strategy,
            "strategy_confidence": ml_decision["strategy_confidence"],
            "predicted_recovery_probability": strategies_eval[final_strategy]["recovery_probability"],
            "expected_recovery_value": strategies_eval[final_strategy]["expected_recovery_value"],
            "policy_result": policy_result,
            "reason_codes": reason_codes,
            "audit_event": audit_event,
        }

    def run_experiment(self, sample_size: int = 100, seed: int = 42) -> Dict[str, Any]:
        """Run counterfactual experiment comparing Revora ML-selected strategy against baseline (always PAYMENT_LINK)."""
        raw_cases = dataset_service.load_dataset()
        if not raw_cases:
            raise ValueError("No recovery cases available to run experiment.")

        rng = random.Random(seed)
        # Sample deterministically from cases
        sample_size = min(sample_size, len(raw_cases))
        cases = rng.sample(raw_cases, sample_size)

        experiment_id = f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        baseline_strategy = "PAYMENT_LINK"
        total_revenue_at_risk = 0.0

        baseline_expected_recovery = 0.0
        revora_expected_recovery = 0.0

        baseline_simulated_recovered_amt = 0.0
        revora_simulated_recovered_amt = 0.0

        baseline_success_count = 0
        revora_success_count = 0

        strategy_counts = {s: 0 for s in STRATEGIES}
        strategy_amounts = {s: 0.0 for s in STRATEGIES}
        strategy_expected_rev = {s: 0.0 for s in STRATEGIES}
        strategy_simulated_recovered_amt = {s: 0.0 for s in STRATEGIES}
        strategy_success_count = {s: 0 for s in STRATEGIES}

        policy_blocked_count = 0
        audit_events: List[Dict[str, Any]] = []

        for idx, case in enumerate(cases):
            amount = float(case["amount"])
            total_revenue_at_risk += amount

            # Counterfactual probabilities for all 4 options
            sim_probs = simulate_counterfactual_strategy_probabilities(case, seed=seed + idx)

            # Baseline evaluation: always PAYMENT_LINK
            base_prob = sim_probs[baseline_strategy]
            base_exp = amount * base_prob
            baseline_expected_recovery += base_exp

            # Simulate baseline realization
            sim_rng = random.Random(seed * 1000 + idx)
            base_recovered = sim_rng.random() < base_prob
            if base_recovered:
                baseline_success_count += 1
                baseline_simulated_recovered_amt += amount

            # Revora Evaluation (Isolate input from ground truth)
            safe_case = {k: v for k, v in case.items() if not k.startswith("ground_truth_")}
            ml_pred = recovery_engine.predict(safe_case)
            raw_strat = ml_pred["recommended_strategy"]
            raw_prob = ml_pred["predicted_recovery_probability"]

            final_strat, pol_res, block_reasons = self.policy.evaluate_guardrails(
                safe_case, raw_strat, raw_prob
            )

            if pol_res == "POLICY_BLOCKED":
                policy_blocked_count += 1

            revora_prob = sim_probs[final_strat]
            revora_exp = amount * revora_prob
            revora_expected_recovery += revora_exp

            # Simulate Revora realization
            revora_recovered = sim_rng.random() < revora_prob
            if revora_recovered:
                revora_success_count += 1
                revora_simulated_recovered_amt += amount

            # Track strategy breakdowns
            strategy_counts[final_strat] += 1
            strategy_amounts[final_strat] += amount
            strategy_expected_rev[final_strat] += revora_exp
            if revora_recovered:
                strategy_success_count[final_strat] += 1
                strategy_simulated_recovered_amt[final_strat] += amount

            reason_codes = list(ml_pred["reason_codes"])
            if block_reasons:
                reason_codes.extend(block_reasons)

            audit_events.append({
                "timestamp": timestamp,
                "transaction_id": case.get("transaction_id", f"txn_{idx}"),
                "selected_strategy": final_strat,
                "confidence": ml_pred["strategy_confidence"],
                "expected_recovery_value": round(revora_exp, 2),
                "policy_result": pol_res,
                "reason_codes": reason_codes,
            })

        # Calculate summaries
        baseline_rec_rate = round(baseline_success_count / sample_size, 4)
        revora_rec_rate = round(revora_success_count / sample_size, 4)

        expected_revenue_difference = round(revora_expected_recovery - baseline_expected_recovery, 2)
        pct_improvement = (
            round((expected_revenue_difference / baseline_expected_recovery) * 100, 2)
            if baseline_expected_recovery > 0
            else 0.0
        )

        strategy_performance = {}
        for s in STRATEGIES:
            cnt = strategy_counts[s]
            strategy_performance[s] = {
                "cases": cnt,
                "total_amount": round(strategy_amounts[s], 2),
                "expected_recovery": round(strategy_expected_rev[s], 2),
                "simulated_recovered_amount": round(strategy_simulated_recovered_amt[s], 2),
                "recovery_rate": round(strategy_success_count[s] / cnt, 4) if cnt > 0 else 0.0,
            }

        result = {
            "experiment_id": experiment_id,
            "timestamp": timestamp,
            "sample_size": sample_size,
            "total_revenue_at_risk": round(total_revenue_at_risk, 2),
            "baseline": {
                "strategy": baseline_strategy,
                "expected_recovery": round(baseline_expected_recovery, 2),
                "simulated_recovered_amount": round(baseline_simulated_recovered_amt, 2),
                "recovery_rate": baseline_rec_rate,
            },
            "revora": {
                "expected_recovery": round(revora_expected_recovery, 2),
                "simulated_recovered_amount": round(revora_simulated_recovered_amt, 2),
                "recovery_rate": revora_rec_rate,
                "policy_blocked_cases": policy_blocked_count,
            },
            "improvement": {
                "expected_revenue_difference": expected_revenue_difference,
                "percentage_improvement": pct_improvement,
                "recovery_rate_lift": round(revora_rec_rate - baseline_rec_rate, 4),
            },
            "strategy_distribution": strategy_counts,
            "strategy_performance": strategy_performance,
            "sample_audit_events": audit_events[:5],  # Sample audit records
        }

        experiment_store.save_experiment(experiment_id, result)
        return result


experiment_engine = ExperimentEngine()
