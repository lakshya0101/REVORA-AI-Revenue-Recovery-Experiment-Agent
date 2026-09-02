from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    transaction_id: Optional[str] = "txn_custom"
    customer_id: Optional[str] = "cust_custom"
    order_id: Optional[str] = "order_custom"
    amount: float = Field(..., ge=0.0, description="Transaction amount in INR")
    currency: Optional[str] = "INR"
    payment_status: str = Field(default="FAILED", description="e.g. FAILED, ABANDONED")
    failure_reason: str = Field(..., description="e.g. BANK_SERVER_DOWN, CHECKOUT_DROPOFF")
    customer_type: str = Field(default="RETURNING", description="FIRST_TIME, RETURNING, VIP, ENTERPRISE")
    previous_successful_payments: int = Field(default=0, ge=0)
    previous_failed_payments: int = Field(default=0, ge=0)
    previous_recovery_attempts: int = Field(default=0, ge=0)
    historical_recovery_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    customer_lifetime_value: float = Field(default=0.0, ge=0.0)
    time_since_failure_minutes: int = Field(default=15, ge=0)
    payment_method: str = Field(default="UPI", description="UPI, CREDIT_CARD, DEBIT_CARD, NET_BANKING, WALLET")
    checkout_abandoned: bool = Field(default=False)
    order_value_segment: Optional[str] = None


class DecisionOutput(BaseModel):
    transaction_id: str
    recommended_strategy: str
    strategy_confidence: float
    predicted_recovery_probability: float
    expected_recovery_value: float
    reason_codes: List[str]
