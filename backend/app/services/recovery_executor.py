from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, Optional
import uuid

from app.services.execution_store import execution_store
from app.services.razorpay_service import razorpay_service
from app.services.recovery_policy import default_policy

logger = logging.getLogger(__name__)


class RecoveryExecutor:
    """Abstraction layer for executing recovery strategies with strict policy enforcement and duplicate protection."""

    def __init__(self) -> None:
        self.policy = default_policy

    def execute_payment_link(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Create a real Razorpay Test Mode Payment Link for the at-risk transaction."""
        client = razorpay_service.get_client()
        if not client:
            return {
                "success": False,
                "strategy": "PAYMENT_LINK",
                "status": "FAILED",
                "mode": "RAZORPAY_TEST",
                "error": "Razorpay client not configured or credentials missing.",
            }

        amount = float(transaction.get("amount", 0.0))
        # Razorpay expects amounts in paise (multiply by 100)
        amount_in_paise = max(100, int(round(amount * 100)))
        txn_id = str(transaction.get("transaction_id", f"txn_{uuid.uuid4().hex[:6]}"))
        reference_id = f"revora_rec_{txn_id}"
        description = f"REVORA Autonomous Revenue Recovery for {txn_id}"

        # 48-hour expiration timestamp
        expire_by = int(time.time()) + (48 * 3600)

        payload = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "reference_id": reference_id,
            "description": description,
            "expire_by": expire_by,
            "reminder_enable": True,
            "notes": {
                "system": "REVORA_RECOVERY_AGENT",
                "transaction_id": txn_id,
                "strategy": "PAYMENT_LINK",
            },
        }

        # Customer details if available
        cust_id = transaction.get("customer_id")
        if cust_id:
            payload["customer"] = {
                "name": f"Customer {cust_id}",
                "contact": "+919876543210",
                "email": f"{cust_id}@example.com",
            }

        try:
            # Create link via Razorpay Python SDK
            link_response = client.payment_link.create(payload)
            link_id = link_response.get("id")
            short_url = link_response.get("short_url")

            return {
                "success": True,
                "strategy": "PAYMENT_LINK",
                "status": "EXECUTED",
                "mode": "RAZORPAY_TEST",
                "payment_link_id": link_id,
                "short_url": short_url,
                "amount": amount,
                "reference_id": reference_id,
            }
        except Exception as e:
            logger.error("Razorpay Payment Link creation error: %s", type(e).__name__)
            return {
                "success": False,
                "strategy": "PAYMENT_LINK",
                "status": "FAILED",
                "mode": "RAZORPAY_TEST",
                "error": f"Failed to create Razorpay Payment Link: {type(e).__name__}",
            }

    def execute_retry(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a controlled safe retry in Test Mode without direct charging."""
        return {
            "success": True,
            "strategy": "RETRY",
            "status": "EXECUTED",
            "mode": "SIMULATED",
            "message": "Retry execution simulated safely in Test Mode",
            "amount": float(transaction.get("amount", 0.0)),
        }

    def execute_alternate_flow(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a controlled alternate payment flow prompt in Test Mode."""
        return {
            "success": True,
            "strategy": "ALTERNATE_FLOW",
            "status": "EXECUTED",
            "mode": "SIMULATED",
            "message": "Alternate payment flow initiated safely in Test Mode",
            "amount": float(transaction.get("amount", 0.0)),
        }

    def execute_no_action(self, transaction: Dict[str, Any], reason: str = "NO_ACTION_REQUIRED") -> Dict[str, Any]:
        """No action execution fallback."""
        return {
            "success": True,
            "strategy": "NO_ACTION",
            "status": "SKIPPED",
            "mode": "NO_ACTION",
            "message": reason,
            "amount": float(transaction.get("amount", 0.0)),
        }

    def execute_recovery(
        self,
        transaction: Dict[str, Any],
        decision: Dict[str, Any],
        is_dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Strict Execution Flow: Decision -> Policy -> Idempotency Check -> Executor -> Audit Store."""
        txn_id = str(transaction.get("transaction_id", "txn_unknown"))
        amount = float(transaction.get("amount", 0.0))
        raw_strategy = decision.get("recommended_strategy", "NO_ACTION")
        predicted_prob = float(decision.get("predicted_recovery_probability", 0.0))

        # 1. Policy Validation (Never bypassed)
        final_strategy, policy_result, blocking_reasons = self.policy.evaluate_guardrails(
            transaction, raw_strategy, predicted_prob
        )

        all_reason_codes = list(decision.get("reason_codes", []))
        if blocking_reasons:
            all_reason_codes.extend(blocking_reasons)

        execution_mode = (
            "RAZORPAY_TEST"
            if final_strategy == "PAYMENT_LINK" and policy_result == "ALLOWED"
            else ("SIMULATED" if final_strategy in ["RETRY", "ALTERNATE_FLOW"] and policy_result == "ALLOWED" else "NO_ACTION")
        )

        # DRY RUN HANDLER (Never invokes Razorpay or updates execution records)
        if is_dry_run:
            return {
                "transaction_id": txn_id,
                "recommended_strategy": final_strategy,
                "policy_result": policy_result,
                "would_execute": (policy_result == "ALLOWED" and final_strategy != "NO_ACTION"),
                "execution_mode": execution_mode,
                "expected_recovery_value": round(amount * predicted_prob, 2),
                "reason_codes": all_reason_codes,
            }

        # 2. Idempotency Check
        existing_record = execution_store.get_by_transaction_id(txn_id)
        if existing_record:
            logger.info("Duplicate execution prevented for %s. Returning existing record.", txn_id)
            return {
                "transaction_id": txn_id,
                "decision": {
                    "strategy": existing_record["strategy"],
                    "confidence": decision.get("strategy_confidence", 1.0),
                    "predicted_recovery_probability": predicted_prob,
                    "expected_recovery_value": round(amount * predicted_prob, 2),
                },
                "policy": {
                    "result": existing_record["policy_result"],
                },
                "execution": {
                    "status": "DUPLICATE_PREVENTED",
                    "mode": existing_record["mode"],
                    "resource_id": existing_record["razorpay_resource_id"],
                    "short_url": existing_record["short_url"],
                    "created_at": existing_record["created_at"],
                },
                "audit_event": existing_record.get("audit_data", {}),
            }

        # 3. Strategy Execution Dispatch
        if policy_result == "POLICY_BLOCKED" or final_strategy == "NO_ACTION":
            exec_res = self.execute_no_action(
                transaction,
                reason="Policy blocked execution" if policy_result == "POLICY_BLOCKED" else "NO_ACTION recommended",
            )
        elif final_strategy == "PAYMENT_LINK":
            exec_res = self.execute_payment_link(transaction)
        elif final_strategy == "RETRY":
            exec_res = self.execute_retry(transaction)
        elif final_strategy == "ALTERNATE_FLOW":
            exec_res = self.execute_alternate_flow(transaction)
        else:
            exec_res = self.execute_no_action(transaction, reason="Unknown strategy")

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        audit_event = {
            "timestamp": timestamp,
            "execution_id": execution_id,
            "transaction_id": txn_id,
            "selected_strategy": final_strategy,
            "confidence": decision.get("strategy_confidence", 0.0),
            "expected_recovery_value": round(amount * predicted_prob, 2),
            "policy_result": policy_result,
            "execution_status": exec_res.get("status"),
            "reason_codes": all_reason_codes,
        }

        # 4. Save to Persistent Execution Store
        store_data = {
            "execution_id": execution_id,
            "transaction_id": txn_id,
            "strategy": final_strategy,
            "status": exec_res.get("status", "EXECUTED"),
            "mode": exec_res.get("mode", execution_mode),
            "razorpay_resource_id": exec_res.get("payment_link_id"),
            "short_url": exec_res.get("short_url"),
            "amount": amount,
            "policy_result": policy_result,
            "error_message": exec_res.get("error"),
            "audit_data": audit_event,
        }
        execution_store.save_execution(store_data)

        return {
            "transaction_id": txn_id,
            "decision": {
                "strategy": final_strategy,
                "confidence": decision.get("strategy_confidence", 0.0),
                "predicted_recovery_probability": predicted_prob,
                "expected_recovery_value": round(amount * predicted_prob, 2),
            },
            "policy": {
                "result": policy_result,
            },
            "execution": {
                "status": exec_res.get("status", "EXECUTED"),
                "mode": exec_res.get("mode", execution_mode),
                "resource_id": exec_res.get("payment_link_id"),
                "short_url": exec_res.get("short_url"),
            },
            "audit_event": audit_event,
        }


recovery_executor = RecoveryExecutor()
