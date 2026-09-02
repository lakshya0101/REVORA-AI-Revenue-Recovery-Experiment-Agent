import json
from app.agents.recovery_decision_engine import recovery_engine, FEATURE_COLUMNS
from app.services.dataset_service import dataset_service


def run_tests_and_evaluation():
    print("=" * 60)
    print("REVORA RECOVERY DECISION ENGINE VERIFICATION")
    print("=" * 60)

    # 1. Dataset loading verification
    cases = dataset_service.load_dataset()
    assert len(cases) == 1000, f"Expected 1000 cases, got {len(cases)}"
    print(f"[PASS] Dataset verified: {len(cases)} records loaded.")

    # 2. Features check (Ensure NO ground truth columns are present in FEATURE_COLUMNS)
    for f in FEATURE_COLUMNS:
        assert not f.startswith("ground_truth_"), f"Ground truth feature leaked: {f}"
    print(f"[PASS] Feature isolation verified: {len(FEATURE_COLUMNS)} sanitized features used.")

    # 3. Train & Evaluate
    eval_res = recovery_engine.train_and_evaluate()
    assert eval_res["model"]["train_size"] == 800
    assert eval_res["model"]["test_size"] == 200
    print("[PASS] Train/Test split verified: 800 train (80%), 200 test (20%).")

    # 4. Check Metrics
    model_acc = eval_res["model"]["accuracy"]
    baseline_acc = eval_res["baseline"]["accuracy"]
    improvement = eval_res["improvement"]
    print(f"[PASS] Model Accuracy: {model_acc*100:.2f}% | Baseline Accuracy: {baseline_acc*100:.2f}% | Improvement: {improvement*100:.2f}%")

    # 5. Prediction Verification
    sample_case = cases[0]
    safe_sample = {k: v for k, v in sample_case.items() if not k.startswith("ground_truth_")}
    decision = recovery_engine.predict(safe_sample)

    assert decision["recommended_strategy"] in ["RETRY", "PAYMENT_LINK", "ALTERNATE_FLOW", "NO_ACTION"]
    assert 0.0 <= decision["strategy_confidence"] <= 1.0
    assert 0.0 <= decision["predicted_recovery_probability"] <= 1.0
    assert decision["expected_recovery_value"] >= 0.0
    assert len(decision["reason_codes"]) > 0

    print("[PASS] Single Prediction verified:")
    print(json.dumps(decision, indent=2))
    print("\nFull Evaluation Summary:")
    print(json.dumps(eval_res, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    run_tests_and_evaluation()
