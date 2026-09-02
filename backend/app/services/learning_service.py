from typing import Any, Dict, List, Optional
from app.services.outcome_store import outcome_store


class LearningService:
    """Service to analyze prediction vs observed outcome calibration, error metrics, and performance signals."""

    @staticmethod
    def analyze_transaction_outcome(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Calculate granular prediction vs outcome error analysis for a single transaction."""
        outcome = outcome_store.get_outcome(transaction_id)
        if not outcome:
            return None

        actual_amt = float(outcome.get("actual_recovered_amount", 0.0))
        expected_amt = float(outcome.get("expected_recovery_value", 0.0))
        pred_prob = float(outcome.get("predicted_recovery_probability", 0.0))
        actual_success = outcome.get("outcome_status") == "RECOVERED" or actual_amt > 0.0

        # Success binary: 1.0 if recovered, 0.0 if not
        actual_binary = 1.0 if actual_success else 0.0
        calibration_error = round(actual_binary - pred_prob, 4)
        prediction_error_amount = round(actual_amt - expected_amt, 2)
        abs_error_amount = round(abs(actual_amt - expected_amt), 2)

        return {
            "transaction_id": transaction_id,
            "prediction": {
                "strategy": outcome.get("strategy"),
                "predicted_recovery_probability": pred_prob,
                "expected_recovery_value": expected_amt,
            },
            "actual": {
                "outcome_status": outcome.get("outcome_status"),
                "outcome_source": outcome.get("outcome_source"),
                "actual_recovered_amount": actual_amt,
                "time_to_recovery_minutes": outcome.get("time_to_recovery_minutes"),
                "observed_at": outcome.get("observed_at"),
            },
            "analysis": {
                "predicted_probability": pred_prob,
                "actual_success": actual_success,
                "calibration_error": calibration_error,
                "expected_recovery_value": expected_amt,
                "actual_recovered_amount": actual_amt,
                "prediction_error_amount": prediction_error_amount,
                "absolute_error_amount": abs_error_amount,
            },
        }

    @staticmethod
    def get_learning_summary(outcome_source: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate learning signals, calibration metrics, and strategy performance across observed outcomes."""
        outcomes = outcome_store.get_outcomes(outcome_source=outcome_source)
        total_observed = len(outcomes)

        if total_observed == 0:
            return {
                "observed_cases": 0,
                "actual_recovered_cases": 0,
                "actual_recovery_rate": 0.0,
                "total_value_at_risk": 0.0,
                "total_expected_recovery": 0.0,
                "total_actual_recovered": 0.0,
                "average_prediction_error": 0.0,
                "average_calibration_error": 0.0,
                "average_time_to_recovery_minutes": 0.0,
                "strategy_performance": {},
                "failure_reason_breakdown": {},
            }

        recovered_cases = sum(1 for o in outcomes if o.get("outcome_status") == "RECOVERED" or o.get("actual_recovered_amount", 0) > 0)
        actual_recovery_rate = round(recovered_cases / total_observed, 4)

        total_val_at_risk = round(sum(float(o.get("transaction_amount", 0.0)) for o in outcomes), 2)
        total_expected_rec = round(sum(float(o.get("expected_recovery_value", 0.0)) for o in outcomes), 2)
        total_actual_rec = round(sum(float(o.get("actual_recovered_amount", 0.0)) for o in outcomes), 2)

        error_amounts = [float(o.get("actual_recovered_amount", 0.0)) - float(o.get("expected_recovery_value", 0.0)) for o in outcomes]
        avg_pred_error = round(sum(error_amounts) / total_observed, 2)

        calibration_errors = [
            (1.0 if (o.get("outcome_status") == "RECOVERED" or o.get("actual_recovered_amount", 0) > 0) else 0.0) - float(o.get("predicted_recovery_probability", 0.0))
            for o in outcomes
        ]
        avg_calibration_error = round(sum(calibration_errors) / total_observed, 4)

        valid_times = [float(o["time_to_recovery_minutes"]) for o in outcomes if o.get("time_to_recovery_minutes") is not None and o.get("time_to_recovery_minutes", 0) > 0]
        avg_time = round(sum(valid_times) / len(valid_times), 2) if valid_times else 0.0

        # Strategy performance grouping
        strategy_stats: Dict[str, Dict[str, Any]] = {}
        for o in outcomes:
            strat = o.get("strategy", "UNKNOWN")
            if strat not in strategy_stats:
                strategy_stats[strat] = {
                    "cases": 0,
                    "recovered": 0,
                    "total_amount": 0.0,
                    "expected_recovery": 0.0,
                    "actual_recovered_amount": 0.0,
                }
            s = strategy_stats[strat]
            s["cases"] += 1
            is_rec = o.get("outcome_status") == "RECOVERED" or float(o.get("actual_recovered_amount", 0)) > 0
            if is_rec:
                s["recovered"] += 1
            s["total_amount"] += float(o.get("transaction_amount", 0.0))
            s["expected_recovery"] += float(o.get("expected_recovery_value", 0.0))
            s["actual_recovered_amount"] += float(o.get("actual_recovered_amount", 0.0))

        # Format recovery rate and rounding
        for strat, stats in strategy_stats.items():
            stats["recovery_rate"] = round(stats["recovered"] / stats["cases"], 4) if stats["cases"] > 0 else 0.0
            stats["total_amount"] = round(stats["total_amount"], 2)
            stats["expected_recovery"] = round(stats["expected_recovery"], 2)
            stats["actual_recovered_amount"] = round(stats["actual_recovered_amount"], 2)

        return {
            "observed_cases": total_observed,
            "actual_recovered_cases": recovered_cases,
            "actual_recovery_rate": actual_recovery_rate,
            "total_value_at_risk": total_val_at_risk,
            "total_expected_recovery": total_expected_rec,
            "total_actual_recovered": total_actual_rec,
            "average_prediction_error": avg_pred_error,
            "average_calibration_error": avg_calibration_error,
            "average_time_to_recovery_minutes": avg_time,
            "strategy_performance": strategy_stats,
        }


learning_service = LearningService()
