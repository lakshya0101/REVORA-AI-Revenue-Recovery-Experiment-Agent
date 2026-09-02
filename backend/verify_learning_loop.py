import json
from app.services.dataset_service import dataset_service
from app.services.execution_store import execution_store
from app.services.learning_service import learning_service
from app.services.outcome_store import outcome_store, RecoveryOutcomeRecord, SessionLocal
from app.services.razorpay_service import razorpay_service


def run_learning_loop_verification():
    print("=" * 60)
    print("REVORA STEP 11: AUDIT & LEARNING LOOP VERIFICATION")
    print("=" * 60)

    # Clean test outcome records from previous runs to ensure clean test state
    db = SessionLocal()
    db.query(RecoveryOutcomeRecord).delete()
    db.commit()
    db.close()

    # 1. Verify Canonical Execution Snapshot exists for txn_syn_0001
    exec_1 = execution_store.get_by_transaction_id("txn_syn_0001")
    assert exec_1 is not None, "Canonical execution record for txn_syn_0001 must exist"
    assert exec_1["strategy"] == "PAYMENT_LINK"
    assert exec_1["strategy_confidence"] is not None
    assert exec_1["predicted_recovery_probability"] is not None
    assert exec_1["expected_recovery_value"] is not None
    assert exec_1["razorpay_resource_id"] is not None
    print(f"[PASS] 1. Verified canonical Step 9 execution snapshot for {exec_1['transaction_id']}:")
    print(f"       Strategy: {exec_1['strategy']}")
    print(f"       Confidence: {exec_1['strategy_confidence']}")
    print(f"       Probability: {exec_1['predicted_recovery_probability']}")
    print(f"       Expected Recovery Value: INR {exec_1['expected_recovery_value']}")
    print(f"       Resource ID: {exec_1['razorpay_resource_id']}")

    # 2. Record simulated outcome using the immutable execution snapshot
    rec_payload_1 = {
        "transaction_id": "txn_syn_0001",
        "execution_id": exec_1["execution_id"],
        "strategy": exec_1["strategy"],
        "transaction_amount": exec_1["amount"],
        "predicted_recovery_probability": exec_1["predicted_recovery_probability"],
        "expected_recovery_value": exec_1["expected_recovery_value"],
        "actual_recovered_amount": exec_1["amount"],
        "outcome_status": "RECOVERED",
        "outcome_source": "SIMULATION",
        "payment_status": "PAID",
        "time_to_recovery_minutes": 18.5,
    }
    out_1 = outcome_store.record_outcome(rec_payload_1)
    assert out_1["outcome_status"] == "RECOVERED"
    assert out_1["actual_recovered_amount"] == exec_1["amount"]
    print(f"[PASS] 2. Recorded simulated recovered outcome for txn_syn_0001 (Source: SIMULATION)")

    # 3. Duplicate outcome idempotently prevented
    dup_out_1 = outcome_store.record_outcome(rec_payload_1)
    assert dup_out_1["outcome_id"] == out_1["outcome_id"]
    print("[PASS] 3. Duplicate outcome idempotently prevented.")

    # 4. Calibration Analysis using the immutable historical snapshot
    analysis_1 = learning_service.analyze_transaction_outcome("txn_syn_0001")
    print("\n--- Canonical Calibration Analysis for txn_syn_0001 ---")
    print(json.dumps(analysis_1, indent=2))
    assert analysis_1["prediction"]["strategy"] == exec_1["strategy"]
    assert analysis_1["prediction"]["predicted_recovery_probability"] == exec_1["predicted_recovery_probability"]
    assert analysis_1["prediction"]["expected_recovery_value"] == exec_1["expected_recovery_value"]
    assert "calibration_error" in analysis_1["analysis"]
    assert "prediction_error_amount" in analysis_1["analysis"]
    print("[PASS] 4. Prediction values match the ORIGINAL execution decision without recomputing.")

    # 5. Record a failed simulated outcome for another transaction (e.g. txn_syn_0002)
    cases = dataset_service.load_dataset()
    txn_2 = cases[1]
    rec_payload_2 = {
        "transaction_id": txn_2["transaction_id"],
        "strategy": "RETRY",
        "transaction_amount": txn_2["amount"],
        "predicted_recovery_probability": 0.65,
        "expected_recovery_value": round(txn_2["amount"] * 0.65, 2),
        "actual_recovered_amount": 0.0,
        "outcome_status": "NOT_RECOVERED",
        "outcome_source": "SIMULATION",
        "payment_status": "FAILED",
        "time_to_recovery_minutes": 0.0,
    }
    out_2 = outcome_store.record_outcome(rec_payload_2)
    assert out_2["outcome_status"] == "NOT_RECOVERED"
    print(f"[PASS] 5. Recorded failed simulated outcome for {txn_2['transaction_id']}")

    # 6. Learning Summary Aggregation
    summary = learning_service.get_learning_summary(outcome_source="SIMULATION")
    print("\n--- Learning Signals Summary (SIMULATION) ---")
    print(json.dumps(summary, indent=2))
    assert summary["observed_cases"] == 2
    assert summary["actual_recovered_cases"] == 1
    assert summary["actual_recovery_rate"] == 0.5
    print("[PASS] 6. Learning summary aggregated across observed simulation outcomes.")

    # 7. Safe Read of Canonical Razorpay Test Payment Link (plink_QhT2eKk9w3qC6a or plink_TXL41IU5yugX64)
    print("\n--- 7. Safe Razorpay Test Payment Link Read ---")
    link_id = exec_1.get("razorpay_resource_id") or "plink_QhT2eKk9w3qC6a"
    link_status = razorpay_service.get_payment_link_status(link_id)
    print(f"Querying Resource: {link_id}")
    print("Razorpay Payment Link Fetch Result:")
    print(json.dumps(link_status, indent=2))
    if link_status.get("success"):
        assert link_status["payment_link_id"] == link_id
        assert link_status["status"] in ["created", "paid", "expired", "cancelled"]
        print(f"[PASS] Successfully read live Razorpay status: {link_status['status']} (Zero new links created).")
    else:
        print(f"[NOTE] Payment link status fetch reported: {link_status.get('error')}")

    print("=" * 60)


if __name__ == "__main__":
    run_learning_loop_verification()
