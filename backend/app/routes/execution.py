from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.agents.recovery_decision_engine import recovery_engine
from app.services.dataset_service import dataset_service
from app.services.execution_store import execution_store
from app.services.recovery_executor import recovery_executor

router = APIRouter(prefix="/api/recovery", tags=["Recovery Execution"])


@router.post("/dry-run/{transaction_id}")
def dry_run_recovery(transaction_id: str):
    """Perform Decision -> Policy -> Planning without calling Razorpay or persisting execution."""
    cases = dataset_service.load_dataset()
    matched_case = next((c for c in cases if c["transaction_id"] == transaction_id), None)

    if not matched_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    safe_txn = {k: v for k, v in matched_case.items() if not k.startswith("ground_truth_")}
    decision = recovery_engine.predict(safe_txn)
    dry_run_result = recovery_executor.execute_recovery(safe_txn, decision, is_dry_run=True)
    return dry_run_result


@router.post("/execute/{transaction_id}")
def execute_recovery_endpoint(transaction_id: str):
    """Execute recovery strategy: Decision -> Policy -> Idempotency -> Executor -> Audit Store."""
    cases = dataset_service.load_dataset()
    matched_case = next((c for c in cases if c["transaction_id"] == transaction_id), None)

    if not matched_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    safe_txn = {k: v for k, v in matched_case.items() if not k.startswith("ground_truth_")}
    decision = recovery_engine.predict(safe_txn)
    execution_result = recovery_executor.execute_recovery(safe_txn, decision, is_dry_run=False)
    return execution_result


@router.get("/executions")
def list_recovery_executions():
    """List execution history and idempotency audit logs."""
    return execution_store.list_executions()
