from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.agents.recovery_decision_engine import recovery_engine
from app.services.dataset_service import dataset_service
from app.services.execution_store import execution_store
from app.services.explanation_agent import explanation_agent
from app.services.recovery_executor import recovery_executor
from app.services.recovery_policy import default_policy

router = APIRouter(prefix="/api/explanations", tags=["Explanations"])


class WhyNotRequest(BaseModel):
    alternative_strategy: str = Field(default="RETRY", description="Strategy to compare against (e.g. RETRY, ALTERNATE_FLOW)")


def _load_and_evaluate_transaction(transaction_id: str) -> Dict[str, Any]:
    """Helper to retrieve transaction and compute or retrieve ML decision & policy context."""
    cases = dataset_service.load_dataset()
    matched = next((c for c in cases if c["transaction_id"] == transaction_id), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found.",
        )

    safe_txn = {k: v for k, v in matched.items() if not k.startswith("ground_truth_")}
    existing_exec = execution_store.get_by_transaction_id(transaction_id)

    if existing_exec and existing_exec.get("strategy_confidence"):
        final_strat = existing_exec["strategy"]
        confidence = existing_exec["strategy_confidence"]
        pred_prob = existing_exec["predicted_recovery_probability"]
        exp_val = existing_exec["expected_recovery_value"]
        pol_res = existing_exec["policy_result"]
        reason_codes = existing_exec.get("reason_codes", [])
    else:
        decision = recovery_engine.predict(safe_txn)
        final_strat, pol_res, block_reasons = default_policy.evaluate_guardrails(
            safe_txn, decision["recommended_strategy"], decision["predicted_recovery_probability"]
        )
        confidence = decision["strategy_confidence"]
        pred_prob = decision["predicted_recovery_probability"]
        exp_val = decision["expected_recovery_value"]
        reason_codes = list(decision.get("reason_codes", []))
        if block_reasons:
            reason_codes.extend(block_reasons)

    context = {
        **safe_txn,
        "recommended_strategy": final_strat,
        "strategy_confidence": confidence,
        "predicted_recovery_probability": pred_prob,
        "expected_recovery_value": exp_val,
        "policy_result": pol_res,
        "reason_codes": reason_codes,
    }
    return context


@router.get("/{transaction_id}")
@router.post("/decision/{transaction_id}")
def explain_decision_endpoint(transaction_id: str):
    """Generate merchant-facing natural language explanation for an ML recovery decision."""
    context = _load_and_evaluate_transaction(transaction_id)
    return explanation_agent.explain_decision(context)


@router.post("/why-not/{transaction_id}")
def explain_why_not_endpoint(transaction_id: str, req: WhyNotRequest):
    """Explain why an alternative recovery strategy was not selected."""
    context = _load_and_evaluate_transaction(transaction_id)
    return explanation_agent.explain_why_not_strategy(context, req.alternative_strategy)


@router.post("/policy/{transaction_id}")
def explain_policy_endpoint(transaction_id: str):
    """Explain why policy guardrails allowed or blocked automated action."""
    context = _load_and_evaluate_transaction(transaction_id)
    return explanation_agent.explain_policy_block(context)


@router.post("/execution/{transaction_id}")
def explain_execution_endpoint(transaction_id: str):
    """Explain recovery execution status and test mode resource generation."""
    context = _load_and_evaluate_transaction(transaction_id)
    existing_record = execution_store.get_by_transaction_id(transaction_id)

    if existing_record:
        context["execution_status"] = existing_record["status"]
        context["execution_mode"] = existing_record["mode"]
        context["resource_id"] = existing_record.get("razorpay_resource_id") or "N/A"
    else:
        context["execution_status"] = "PENDING_OR_DRY_RUN"
        context["execution_mode"] = "SIMULATED"
        context["resource_id"] = "N/A"

    return explanation_agent.explain_execution(context)
