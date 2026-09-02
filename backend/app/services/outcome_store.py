import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base, SessionLocal, engine


class RecoveryOutcomeRecord(Base):
    __tablename__ = "recovery_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=False)
    transaction_id = Column(String(64), index=True, nullable=False)
    execution_id = Column(String(64), nullable=True)
    strategy = Column(String(32), nullable=False)
    transaction_amount = Column(Float, nullable=False)
    predicted_recovery_probability = Column(Float, nullable=False)
    expected_recovery_value = Column(Float, nullable=False)
    actual_recovered_amount = Column(Float, nullable=False)
    outcome_status = Column(String(32), nullable=False)  # PENDING, RECOVERED, NOT_RECOVERED, EXPIRED, CANCELLED, UNKNOWN
    outcome_source = Column(String(32), nullable=False)  # RAZORPAY_TEST, SIMULATION, MANUAL, MODEL
    payment_status = Column(String(32), nullable=False)  # PAID, FAILED, PENDING, EXPIRED, etc.
    payment_event_id = Column(String(64), nullable=True)
    time_to_recovery_minutes = Column(Float, nullable=True)
    failure_reason = Column(String(64), nullable=True)
    customer_type = Column(String(32), nullable=True)
    payment_method = Column(String(32), nullable=True)
    order_value_segment = Column(String(32), nullable=True)
    observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Ensure table creation in SQLite
Base.metadata.create_all(bind=engine)


class OutcomeStore:
    """Persistent SQLite store for observed recovery outcomes with strict idempotency."""

    @staticmethod
    def get_by_idempotency_key(idempotency_key: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            record = (
                db.query(RecoveryOutcomeRecord)
                .filter(RecoveryOutcomeRecord.idempotency_key == idempotency_key)
                .first()
            )
            if not record:
                return None
            return OutcomeStore._to_dict(record)
        finally:
            db.close()

    @staticmethod
    def get_outcome(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve most recent outcome for a transaction."""
        db = SessionLocal()
        try:
            record = (
                db.query(RecoveryOutcomeRecord)
                .filter(RecoveryOutcomeRecord.transaction_id == transaction_id)
                .order_by(RecoveryOutcomeRecord.id.desc())
                .first()
            )
            if not record:
                return None
            return OutcomeStore._to_dict(record)
        finally:
            db.close()

    @staticmethod
    def record_outcome(data: Dict[str, Any]) -> Dict[str, Any]:
        """Record or idempotently return an outcome record."""
        idempotency_key = data.get("idempotency_key")
        if not idempotency_key:
            event_id = data.get("payment_event_id")
            if event_id:
                idempotency_key = f"{data['transaction_id']}_{event_id}"
            else:
                idempotency_key = f"{data['transaction_id']}_{data.get('outcome_source', 'MANUAL')}_{data.get('payment_status')}"

        existing = OutcomeStore.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        outcome_id = data.get("outcome_id") or f"out_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        db = SessionLocal()
        try:
            record = RecoveryOutcomeRecord(
                outcome_id=outcome_id,
                idempotency_key=idempotency_key,
                transaction_id=data["transaction_id"],
                execution_id=data.get("execution_id"),
                strategy=data.get("strategy", "NO_ACTION"),
                transaction_amount=float(data.get("transaction_amount", 0.0)),
                predicted_recovery_probability=float(data.get("predicted_recovery_probability", 0.0)),
                expected_recovery_value=float(data.get("expected_recovery_value", 0.0)),
                actual_recovered_amount=float(data.get("actual_recovered_amount", 0.0)),
                outcome_status=data.get("outcome_status", "PENDING"),
                outcome_source=data.get("outcome_source", "RAZORPAY_TEST"),
                payment_status=data.get("payment_status", "PENDING"),
                payment_event_id=data.get("payment_event_id"),
                time_to_recovery_minutes=float(data.get("time_to_recovery_minutes", 0.0)) if data.get("time_to_recovery_minutes") is not None else None,
                failure_reason=data.get("failure_reason"),
                customer_type=data.get("customer_type"),
                payment_method=data.get("payment_method"),
                order_value_segment=data.get("order_value_segment"),
                observed_at=now,
                created_at=now,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return OutcomeStore._to_dict(record)
        finally:
            db.close()

    @staticmethod
    def get_outcomes(outcome_source: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """List outcome records, optionally filtered by outcome_source."""
        db = SessionLocal()
        try:
            query = db.query(RecoveryOutcomeRecord).order_by(RecoveryOutcomeRecord.id.desc())
            if outcome_source:
                query = query.filter(RecoveryOutcomeRecord.outcome_source == outcome_source)
            records = query.limit(limit).all()
            return [OutcomeStore._to_dict(r) for r in records]
        finally:
            db.close()

    @staticmethod
    def _to_dict(record: RecoveryOutcomeRecord) -> Dict[str, Any]:
        return {
            "outcome_id": record.outcome_id,
            "idempotency_key": record.idempotency_key,
            "transaction_id": record.transaction_id,
            "execution_id": record.execution_id,
            "strategy": record.strategy,
            "transaction_amount": record.transaction_amount,
            "predicted_recovery_probability": record.predicted_recovery_probability,
            "expected_recovery_value": record.expected_recovery_value,
            "actual_recovered_amount": record.actual_recovered_amount,
            "outcome_status": record.outcome_status,
            "outcome_source": record.outcome_source,
            "payment_status": record.payment_status,
            "payment_event_id": record.payment_event_id,
            "time_to_recovery_minutes": record.time_to_recovery_minutes,
            "failure_reason": record.failure_reason,
            "customer_type": record.customer_type,
            "payment_method": record.payment_method,
            "order_value_segment": record.order_value_segment,
            "observed_at": record.observed_at.isoformat() if record.observed_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


outcome_store = OutcomeStore()
