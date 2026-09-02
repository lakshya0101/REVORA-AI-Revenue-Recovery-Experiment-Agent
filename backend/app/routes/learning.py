from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.services.learning_service import learning_service

router = APIRouter(prefix="/api/learning", tags=["Learning & Calibration"])


@router.get("/summary")
def get_learning_summary(
    outcome_source: Optional[str] = Query(default=None, description="Optional filter: RAZORPAY_TEST, SIMULATION, MANUAL")
):
    """Retrieve learning signals, calibration metrics, and strategy performance summary."""
    return learning_service.get_learning_summary(outcome_source=outcome_source)


@router.get("/transaction/{transaction_id}")
def get_transaction_learning_analysis(transaction_id: str):
    """Retrieve detailed prediction vs actual outcome comparison and calibration analysis for a transaction."""
    analysis = learning_service.analyze_transaction_outcome(transaction_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No observed outcome found for transaction '{transaction_id}'.",
        )
    return analysis
