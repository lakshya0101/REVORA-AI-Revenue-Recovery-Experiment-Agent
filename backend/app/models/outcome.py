from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OutcomeRecordInput(BaseModel):
    transaction_id: str = Field(..., description="Transaction ID being tracked")
    execution_id: Optional[str] = Field(default=None, description="Nullable execution ID")
    outcome_source: str = Field(default="RAZORPAY_TEST", description="RAZORPAY_TEST, SIMULATION, MANUAL, or MODEL")
    payment_event_id: Optional[str] = Field(default=None, description="Idempotency payment event identifier")
    payment_status: str = Field(default="PAID", description="e.g. PAID, FAILED, PENDING, EXPIRED, CANCELLED")
    actual_recovered_amount: float = Field(default=0.0, ge=0.0, description="Observed recovered amount")
    time_to_recovery_minutes: Optional[float] = Field(default=0.0, ge=0.0)


class SimulatedOutcomeInput(BaseModel):
    transaction_id: str
    payment_status: str = Field(default="PAID", description="PAID or FAILED")
    recovered_amount: float = Field(default=0.0, ge=0.0)
    time_to_recovery_minutes: Optional[float] = Field(default=15.0, ge=0.0)


class OutcomeResponse(BaseModel):
    outcome_id: str
    transaction_id: str
    execution_id: Optional[str] = None
    strategy: str
    outcome_status: str
    outcome_source: str
    actual_recovered_amount: float
    expected_recovery_value: float
    time_to_recovery_minutes: Optional[float] = None
    observed_at: Optional[str] = None


class OutcomeStatusDetail(BaseModel):
    transaction_id: str
    prediction: Dict[str, Any]
    execution: Dict[str, Any]
    outcome: Dict[str, Any]
