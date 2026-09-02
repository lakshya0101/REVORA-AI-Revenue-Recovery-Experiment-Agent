import json
from app.services.experiment_engine import experiment_engine
from app.services.recovery_policy import default_policy


def run_experiment_verification():
    print("=" * 60)
    print("REVORA RECOVERY EXPERIMENT ENGINE VERIFICATION (100 CASES)")
    print("=" * 60)

    # 1. Run 100-case experiment
    exp = experiment_engine.run_experiment(sample_size=100, seed=42)

    print(f"Experiment ID: {exp['experiment_id']}")
    print(f"Sample Size: {exp['sample_size']}")
    print(f"Total Revenue At Risk: INR {exp['total_revenue_at_risk']:,.2f}\n")

    print(f"1. Baseline Recovery Rate: {exp['baseline']['recovery_rate']*100:.2f}%")
    print(f"2. Revora Recovery Rate: {exp['revora']['recovery_rate']*100:.2f}% (Lift: +{exp['improvement']['recovery_rate_lift']*100:.2f}%)")
    print(f"3. Baseline Expected Recovery: INR {exp['baseline']['expected_recovery']:,.2f}")
    print(f"4. Revora Expected Recovery: INR {exp['revora']['expected_recovery']:,.2f}")
    print(f"5. Revenue Improvement: INR {exp['improvement']['expected_revenue_difference']:,.2f} (+{exp['improvement']['percentage_improvement']}%)")
    print(f"6. Strategy Distribution: {json.dumps(exp['strategy_distribution'], indent=2)}")
    print(f"7. Per-Strategy Performance:\n{json.dumps(exp['strategy_performance'], indent=2)}")
    print(f"8. Policy Blocked Cases: {exp['revora']['policy_blocked_cases']}")

    print("\n9. Sample Audit Event:")
    print(json.dumps(exp["sample_audit_events"][0], indent=2))

    # 2. Evaluate single transaction options
    sample_txn = {
        "transaction_id": "txn_demo_999",
        "amount": 45000.0,
        "payment_status": "FAILED",
        "failure_reason": "BANK_SERVER_DOWN",
        "customer_type": "RETURNING",
        "previous_successful_payments": 12,
        "previous_failed_payments": 1,
        "previous_recovery_attempts": 0,
        "historical_recovery_rate": 0.85,
        "customer_lifetime_value": 35000.0,
        "time_since_failure_minutes": 10,
        "payment_method": "UPI",
        "checkout_abandoned": False,
    }
    eval_opts = experiment_engine.evaluate_strategy_options(sample_txn)
    print("\nSingle Transaction Strategy Evaluation (`evaluate-options`):")
    print(json.dumps(eval_opts, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    run_experiment_verification()
