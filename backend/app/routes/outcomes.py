from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.agents.recovery_decision_engine import recovery_engine
from app.models.outcome import OutcomeRecordInput, OutcomeResponse, OutcomeStatusDetail, SimulatedOutcomeInput
from app.services.dataset_service import dataset_service
from app.services.execution_store import execution_store
from app.services.learning_service import learning_service
from app.services.outcome_store import outcome_store
from app.services.recovery_policy import default_policy

router = APIRouter(prefix="/api/outcomes", tags=["Outcomes & Learning Loop"])


@router.post("/record", response_model=OutcomeResponse)
def record_outcome_endpoint(req: OutcomeRecordInput):
    """Record an observed payment/recovery outcome with strict validation."""
    cases = dataset_service.load_dataset()
    matched = next((c for c in cases if c["transaction_id"] == req.transaction_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{req.transaction_id}' not found.",
        )

    txn_amount = float(matched["amount"])

    # Validation: Source allowed
    allowed_sources = ["RAZORPAY_TEST", "SIMULATION", "MANUAL", "MODEL"]
    if req.outcome_source not in allowed_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outcome_source '{req.outcome_source}'. Must be one of {allowed_sources}",
        )

    # Validation: Amount bounds
    if req.actual_recovered_amount < 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="actual_recovered_amount cannot be negative.",
        )
    if req.actual_recovered_amount > txn_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"actual_recovered_amount ({req.actual_recovered_amount}) cannot exceed transaction amount ({txn_amount}).",
        )

    # Validation: Recovery vs payment status
    payment_status_upper = req.payment_status.upper()
    if payment_status_upper not in ["PAID", "CAPTURED", "SETTLED"] and req.actual_recovered_amount > 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record positive recovered amount when payment status is not successful (PAID/CAPTURED/SETTLED).",
        )

    # Execution link validation
    if req.execution_id:
        existing_exec = execution_store.get_by_transaction_id(req.transaction_id)
        if not existing_exec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution '{req.execution_id}' not found for transaction '{req.transaction_id}'.",
            )

    # Determine status & prediction context: Prioritize IMMUTABLE execution snapshot if transaction was executed
    existing_exec = execution_store.get_by_transaction_id(req.transaction_id)
    if existing_exec and existing_exec.get("strategy_confidence"):
        strategy = existing_exec["strategy"]
        pred_prob = existing_exec["predicted_recovery_probability"]
        expected_val = existing_exec["expected_recovery_value"]
    else:
        safe_txn = {k: v for k, v in matched.items() if not k.startswith("ground_truth_")}
        decision = recovery_engine.predict(safe_txn)
        strategy = decision["recommended_strategy"]
        pred_prob = decision["predicted_recovery_probability"]
        expected_val = decision["expected_recovery_value"]

    outcome_status = "RECOVERED" if (payment_status_upper in ["PAID", "CAPTURED", "SETTLED"] and req.actual_recovered_amount > 0.0) else "NOT_RECOVERED"
    if payment_status_upper == "PENDING":
        outcome_status = "PENDING"
    elif payment_status_upper in ["EXPIRED", "CANCELLED"]:
        outcome_status = payment_status_upper

    store_payload = {
        "transaction_id": req.transaction_id,
        "execution_id": req.execution_id or (existing_exec.get("execution_id") if existing_exec else None),
        "strategy": strategy,
        "transaction_amount": txn_amount,
        "predicted_recovery_probability": pred_prob,
        "expected_recovery_value": expected_val,
        "actual_recovered_amount": req.actual_recovered_amount,
        "outcome_status": outcome_status,
        "outcome_source": req.outcome_source,
        "payment_status": payment_status_upper,
        "payment_event_id": req.payment_event_id,
        "time_to_recovery_minutes": req.time_to_recovery_minutes,
        "failure_reason": matched.get("failure_reason"),
        "customer_type": matched.get("customer_type"),
        "payment_method": matched.get("payment_method"),
        "order_value_segment": matched.get("order_value_segment"),
    }

    res = outcome_store.record_outcome(store_payload)
    return res


@router.post("/simulate", response_model=OutcomeResponse)
def simulate_outcome_endpoint(req: SimulatedOutcomeInput):
    """Development/Demo endpoint to record a SIMULATION outcome without calling Razorpay."""
    cases = dataset_service.load_dataset()
    matched = next((c for c in cases if c["transaction_id"] == req.transaction_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{req.transaction_id}' not found.",
        )

    txn_amount = float(matched["amount"])
    if req.recovered_amount < 0 or req.recovered_amount > txn_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recovered amount: {req.recovered_amount}",
        )

    existing_exec = execution_store.get_by_transaction_id(req.transaction_id)
    if existing_exec and existing_exec.get("strategy_confidence"):
        strategy = existing_exec["strategy"]
        pred_prob = existing_exec["predicted_recovery_probability"]
        expected_val = existing_exec["expected_recovery_value"]
    else:
        safe_txn = {k: v for k, v in matched.items() if not k.startswith("ground_truth_")}
        decision = recovery_engine.predict(safe_txn)
        strategy = decision["recommended_strategy"]
        pred_prob = decision["predicted_recovery_probability"]
        expected_val = decision["expected_recovery_value"]

    payment_status_upper = req.payment_status.upper()
    outcome_status = "RECOVERED" if payment_status_upper == "PAID" and req.recovered_amount > 0 else "NOT_RECOVERED"

    store_payload = {
        "transaction_id": req.transaction_id,
        "execution_id": existing_exec.get("execution_id") if existing_exec else None,
        "strategy": strategy,
        "transaction_amount": txn_amount,
        "predicted_recovery_probability": pred_prob,
        "expected_recovery_value": expected_val,
        "actual_recovered_amount": req.recovered_amount,
        "outcome_status": outcome_status,
        "outcome_source": "SIMULATION",
        "payment_status": payment_status_upper,
        "time_to_recovery_minutes": req.time_to_recovery_minutes or 15.0,
        "failure_reason": matched.get("failure_reason"),
        "customer_type": matched.get("customer_type"),
        "payment_method": matched.get("payment_method"),
        "order_value_segment": matched.get("order_value_segment"),
    }
    return outcome_store.record_outcome(store_payload)


@router.get("/{transaction_id}")
def get_transaction_outcome_status(transaction_id: str):
    """Retrieve full Prediction -> Execution -> Observed Outcome status for a transaction."""
    cases = dataset_service.load_dataset()
    matched = next((c for c in cases if c["transaction_id"] == transaction_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found.",
        )

    execution_record = execution_store.get_by_transaction_id(transaction_id)
    outcome_record = outcome_store.get_outcome(transaction_id)

    if execution_record and execution_record.get("strategy_confidence"):
        prediction_view = {
            "strategy": execution_record["strategy"],
            "confidence": execution_record["strategy_confidence"],
            "probability": execution_record["predicted_recovery_probability"],
            "expected_recovery_value": execution_record["expected_recovery_value"],
            "reason_codes": execution_record.get("reason_codes", []),
        }
    else:
        safe_txn = {k: v for k, v in matched.items() if not k.startswith("ground_truth_")}
        decision = recovery_engine.predict(safe_txn)
        prediction_view = {
            "strategy": decision["recommended_strategy"],
            "confidence": decision["strategy_confidence"],
            "probability": decision["predicted_recovery_probability"],
            "expected_recovery_value": decision["expected_recovery_value"],
            "reason_codes": decision["reason_codes"],
        }

    execution_view = {
        "status": execution_record["status"] if execution_record else "NOT_EXECUTED",
        "mode": execution_record["mode"] if execution_record else "NONE",
        "resource_id": execution_record.get("razorpay_resource_id") if execution_record else None,
        "short_url": execution_record.get("short_url") if execution_record else None,
    }

    if outcome_record:
        outcome_view = {
            "status": outcome_record["outcome_status"],
            "actual_recovered_amount": outcome_record["actual_recovered_amount"],
            "outcome_source": outcome_record["outcome_source"],
            "time_to_recovery_minutes": outcome_record.get("time_to_recovery_minutes"),
            "observed_at": outcome_record.get("observed_at"),
        }
    else:
        outcome_view = {
            "status": "PENDING",
            "actual_recovered_amount": 0.0,
            "outcome_source": "NONE",
            "time_to_recovery_minutes": None,
            "observed_at": None,
        }

    return {
        "transaction_id": transaction_id,
        "prediction": prediction_view,
        "execution": execution_view,
        "outcome": outcome_view,
    }
