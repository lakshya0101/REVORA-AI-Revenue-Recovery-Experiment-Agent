import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.database import Base, SessionLocal, engine


class RecoveryExecutionRecord(Base):
    __tablename__ = "recovery_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), unique=True, index=True, nullable=False)
    transaction_id = Column(String(64), index=True, nullable=False)
    strategy = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)  # EXECUTED, SKIPPED, FAILED
    mode = Column(String(32), nullable=False)    # RAZORPAY_TEST, SIMULATED, NO_ACTION
    razorpay_resource_id = Column(String(64), nullable=True)
    short_url = Column(String(256), nullable=True)
    amount = Column(Float, nullable=False)
    policy_result = Column(String(32), nullable=False)
    error_message = Column(Text, nullable=True)
    audit_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Ensure table creation
Base.metadata.create_all(bind=engine)


class ExecutionStore:
    """Persistent SQLite store for idempotency tracking and duplicate execution prevention."""

    @staticmethod
    def get_by_transaction_id(transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve existing execution record for a transaction if one exists."""
        db = SessionLocal()
        try:
            record = (
                db.query(RecoveryExecutionRecord)
                .filter(RecoveryExecutionRecord.transaction_id == transaction_id)
                .order_by(RecoveryExecutionRecord.id.desc())
                .first()
            )
            if not record:
                return None
            return {
                "execution_id": record.execution_id,
                "transaction_id": record.transaction_id,
                "strategy": record.strategy,
                "status": record.status,
                "mode": record.mode,
                "razorpay_resource_id": record.razorpay_resource_id,
                "short_url": record.short_url,
                "amount": record.amount,
                "policy_result": record.policy_result,
                "error_message": record.error_message,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "audit_data": json.loads(record.audit_data) if record.audit_data else {},
            }
        finally:
            db.close()

    @staticmethod
    def save_execution(data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a new execution record into SQLite."""
        db = SessionLocal()
        try:
            audit_json = json.dumps(data.get("audit_data", {}))
            record = RecoveryExecutionRecord(
                execution_id=data["execution_id"],
                transaction_id=data["transaction_id"],
                strategy=data["strategy"],
                status=data["status"],
                mode=data["mode"],
                razorpay_resource_id=data.get("razorpay_resource_id"),
                short_url=data.get("short_url"),
                amount=float(data.get("amount", 0.0)),
                policy_result=data.get("policy_result", "ALLOWED"),
                error_message=data.get("error_message"),
                audit_data=audit_json,
                created_at=datetime.now(timezone.utc),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return {
                "execution_id": record.execution_id,
                "transaction_id": record.transaction_id,
                "strategy": record.strategy,
                "status": record.status,
                "mode": record.mode,
                "razorpay_resource_id": record.razorpay_resource_id,
                "short_url": record.short_url,
                "amount": record.amount,
                "policy_result": record.policy_result,
                "created_at": record.created_at.isoformat(),
            }
        finally:
            db.close()

    @staticmethod
    def list_executions(limit: int = 50) -> List[Dict[str, Any]]:
        """List recent execution records."""
        db = SessionLocal()
        try:
            records = (
                db.query(RecoveryExecutionRecord)
                .order_by(RecoveryExecutionRecord.id.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "execution_id": r.execution_id,
                    "transaction_id": r.transaction_id,
                    "strategy": r.strategy,
                    "status": r.status,
                    "mode": r.mode,
                    "razorpay_resource_id": r.razorpay_resource_id,
                    "short_url": r.short_url,
                    "amount": r.amount,
                    "policy_result": r.policy_result,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in records
            ]
        finally:
            db.close()


execution_store = ExecutionStore()
