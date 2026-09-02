from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.agents.recovery_decision_engine import recovery_engine
from app.models.recovery import DecisionOutput, TransactionInput
from app.services.dataset_service import dataset_service
from app.services.experiment_engine import experiment_engine

router = APIRouter(prefix="/api/recovery", tags=["Recovery Engine"])


@router.get("/evaluation")
def get_model_evaluation() -> Dict[str, Any]:
    """Return comprehensive held-out test evaluation metrics for the recovery decision engine."""
    return recovery_engine.get_evaluation()


@router.get("/predict/{transaction_id}", response_model=DecisionOutput)
def predict_by_transaction_id(transaction_id: str):
    """Load a transaction from the synthetic dataset (excluding ground truth) and run prediction."""
    cases = dataset_service.load_dataset()
    matched_case = next((c for c in cases if c["transaction_id"] == transaction_id), None)

    if not matched_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' was not found in the dataset.",
        )

    # Exclude all ground-truth fields
    safe_transaction = {k: v for k, v in matched_case.items() if not k.startswith("ground_truth_")}
    decision = recovery_engine.predict(safe_transaction)
    return decision


@router.post("/predict", response_model=DecisionOutput)
def predict_transaction(transaction: TransactionInput):
    """Predict the optimal recovery strategy and expected recovery value for any transaction payload."""
    payload = transaction.model_dump()
    if not payload.get("order_value_segment"):
        from app.services.synthetic_data_generator import determine_value_segment
        payload["order_value_segment"] = determine_value_segment(payload["amount"])

    decision = recovery_engine.predict(payload)
    return decision


@router.post("/evaluate-options")
def evaluate_options(transaction: TransactionInput):
    """Evaluate all 4 recovery options with counterfactuals and return recommended strategy with guardrails."""
    payload = transaction.model_dump()
    if not payload.get("order_value_segment"):
        from app.services.synthetic_data_generator import determine_value_segment
        payload["order_value_segment"] = determine_value_segment(payload["amount"])

    return experiment_engine.evaluate_strategy_options(payload)
