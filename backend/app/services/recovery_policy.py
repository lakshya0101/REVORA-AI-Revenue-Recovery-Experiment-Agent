from typing import Any, Dict, List, Tuple

# Allowed baseline recovery strategies
ALLOWED_STRATEGIES = ["RETRY", "PAYMENT_LINK", "ALTERNATE_FLOW", "NO_ACTION"]

# Default Merchant Guardrail Thresholds
DEFAULT_MAX_RECOVERY_ATTEMPTS: int = 2
DEFAULT_MAX_AUTO_ACTION_AMOUNT: float = 100000.0  # Max ₹1,00,000 for autonomous action
DEFAULT_MIN_RECOVERY_PROBABILITY: float = 0.35     # Fallback to NO_ACTION if lower


class RecoveryPolicyGuardrail:
    """Configurable safety policies and merchant guardrails for autonomous revenue recovery."""

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_RECOVERY_ATTEMPTS,
        max_auto_amount: float = DEFAULT_MAX_AUTO_ACTION_AMOUNT,
        min_probability: float = DEFAULT_MIN_RECOVERY_PROBABILITY,
        allowed_strategies: List[str] = ALLOWED_STRATEGIES,
    ) -> None:
        self.max_attempts = max_attempts
        self.max_auto_amount = max_auto_amount
        self.min_probability = min_probability
        self.allowed_strategies = allowed_strategies

    def evaluate_guardrails(
        self,
        transaction: Dict[str, Any],
        recommended_strategy: str,
        predicted_probability: float,
    ) -> Tuple[str, str, List[str]]:
        """Validate proposed strategy against merchant guardrails.

        Returns:
            final_strategy: str
            policy_result: 'ALLOWED' | 'POLICY_BLOCKED'
            blocking_reasons: List[str]
        """
        blocking_reasons: List[str] = []
        amount = float(transaction.get("amount", 0.0))
        prev_attempts = int(transaction.get("previous_recovery_attempts", 0))

        if recommended_strategy == "NO_ACTION":
            return "NO_ACTION", "ALLOWED", []

        # Guardrail 1: Max recovery attempts check
        if prev_attempts >= self.max_attempts:
            blocking_reasons.append("POLICY_EXCEEDED_MAX_RECOVERY_ATTEMPTS")

        # Guardrail 2: Max transaction amount eligible for automatic action
        if amount > self.max_auto_amount:
            blocking_reasons.append("POLICY_EXCEEDS_AUTO_ACTION_AMOUNT_LIMIT")

        # Guardrail 3: Minimum recovery probability requirement
        if predicted_probability < self.min_probability:
            blocking_reasons.append("POLICY_BELOW_MIN_RECOVERY_PROBABILITY")

        # Guardrail 4: Supported strategies check
        if recommended_strategy not in self.allowed_strategies:
            blocking_reasons.append("POLICY_UNSUPPORTED_STRATEGY")

        if blocking_reasons:
            return "NO_ACTION", "POLICY_BLOCKED", blocking_reasons

        return recommended_strategy, "ALLOWED", []


default_policy = RecoveryPolicyGuardrail()
