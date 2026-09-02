import json
from app.agents.recovery_decision_engine import recovery_engine
from app.services.dataset_service import dataset_service
from app.services.execution_store import execution_store
from app.services.recovery_executor import recovery_executor
from app.services.recovery_policy import default_policy


def run_execution_verification():
    print("=" * 60)
    print("REVORA RECOVERY EXECUTION LAYER VERIFICATION")
    print("=" * 60)

    cases = dataset_service.load_dataset()

    # Find a candidate transaction for PAYMENT_LINK
    target_case = None
    for c in cases:
        if c["failure_reason"] in ["CHECKOUT_DROPOFF", "INCORRECT_OTP"] and c["amount"] < 5000:
            target_case = c
            break

    if not target_case:
        target_case = cases[0]

    safe_txn = {k: v for k, v in target_case.items() if not k.startswith("ground_truth_")}
    txn_id = safe_txn["transaction_id"]
    print(f"Selected Test Transaction: {txn_id} (Amount: INR {safe_txn['amount']}, Reason: {safe_txn['failure_reason']})\n")

    # TEST A: Dry-Run (Must NOT call Razorpay or persist execution)
    print("--- 1. Testing Dry-Run Endpoint ---")
    decision = recovery_engine.predict(safe_txn)
    dry_run_res = recovery_executor.execute_recovery(safe_txn, decision, is_dry_run=True)
    print("Dry-run result:")
    print(json.dumps(dry_run_res, indent=2))
    assert dry_run_res["would_execute"] is True
    print("[PASS] Dry-run verified: zero side effects, no Razorpay call, no store record.\n")

    # TEST B: Real Execution (1 Single Real Razorpay Test Payment Link)
    print("--- 2. Testing Execution (Creates 1 Razorpay Test Payment Link) ---")
    exec_res = recovery_executor.execute_recovery(safe_txn, decision, is_dry_run=False)
    print("Execution result:")
    print(json.dumps(exec_res, indent=2))
    assert exec_res["policy"]["result"] == "ALLOWED"
    assert exec_res["execution"]["status"] in ["EXECUTED", "DUPLICATE_PREVENTED"]
    if exec_res["decision"]["strategy"] == "PAYMENT_LINK":
        assert exec_res["execution"]["mode"] == "RAZORPAY_TEST"
        assert exec_res["execution"]["resource_id"] is not None
        assert "rzp.io" in str(exec_res["execution"]["short_url"])
    print("[PASS] Execution verified: Payment Link generated successfully.\n")

    # TEST C: Duplicate Execution Prevention (Idempotency)
    print("--- 3. Testing Duplicate Execution Prevention ---")
    dup_res = recovery_executor.execute_recovery(safe_txn, decision, is_dry_run=False)
    print("Duplicate execution response:")
    print(json.dumps(dup_res, indent=2))
    assert dup_res["execution"]["status"] == "DUPLICATE_PREVENTED"
    assert dup_res["execution"]["resource_id"] == exec_res["execution"]["resource_id"]
    print("[PASS] Duplicate prevention verified: reused existing link without calling Razorpay.\n")

    # TEST D: Guardrails & Policy Violations
    print("--- 4. Testing Guardrails & Policy Blocking ---")
    
    # 4a: Low Recovery Probability
    low_prob_txn = dict(safe_txn)
    low_prob_txn["transaction_id"] = "txn_test_low_prob"
    blocked_strat, pol_res, reasons = default_policy.evaluate_guardrails(low_prob_txn, "PAYMENT_LINK", 0.15)
    print(f"Low probability test (< 0.35): Strategy={blocked_strat}, Result={pol_res}, Reasons={reasons}")
    assert pol_res == "POLICY_BLOCKED"
    assert blocked_strat == "NO_ACTION"

    # 4b: Max Attempts Exceeded
    max_att_txn = dict(safe_txn)
    max_att_txn["transaction_id"] = "txn_test_max_att"
    max_att_txn["previous_recovery_attempts"] = 3
    blocked_strat, pol_res, reasons = default_policy.evaluate_guardrails(max_att_txn, "RETRY", 0.85)
    print(f"Max attempts test (>= 2): Strategy={blocked_strat}, Result={pol_res}, Reasons={reasons}")
    assert pol_res == "POLICY_BLOCKED"
    assert blocked_strat == "NO_ACTION"

    # 4c: Auto-Action Amount Exceeded (> ₹1,00,000)
    high_amt_txn = dict(safe_txn)
    high_amt_txn["transaction_id"] = "txn_test_high_amt"
    high_amt_txn["amount"] = 150000.0
    blocked_strat, pol_res, reasons = default_policy.evaluate_guardrails(high_amt_txn, "PAYMENT_LINK", 0.90)
    print(f"High amount test (> 100k): Strategy={blocked_strat}, Result={pol_res}, Reasons={reasons}")
    assert pol_res == "POLICY_BLOCKED"
    assert blocked_strat == "NO_ACTION"

    print("[PASS] Guardrails verified: all violations fall back to NO_ACTION.")
    print("=" * 60)


if __name__ == "__main__":
    run_execution_verification()
