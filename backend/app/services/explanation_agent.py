from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)

# Deterministic human-readable mapping of reason codes
REASON_CODE_EXPLANATIONS: Dict[str, str] = {
    "USER_AUTHENTICATION_DROPOFF": "The failure pattern suggests the customer did not complete user authentication or OTP verification.",
    "FIRST_TIME_BUYER": "This is a first-time customer with no prior transaction history on file.",
    "HIGH_RECOVERY_POTENTIAL": "The model estimates strong recovery potential based on transaction context and time elapsed.",
    "TEMPORARY_SYSTEM_FAILURE": "The failure appears consistent with a temporary bank or network timeout.",
    "STRONG_CUSTOMER_HISTORY": "The customer has a reliable historical payment and recovery track record.",
    "IMMEDIATE_RECOVERY_WINDOW": "The transaction failed recently and is currently within the optimal recovery conversion window.",
    "METHOD_SPECIFIC_ISSUE": "The failure indicates an issue specific to the selected payment method (e.g. card expiry or unresponsive app).",
    "FINANCIAL_LIMIT_CONSTRAINT": "The transaction encountered insufficient funds or banking limit constraints.",
    "CHECKOUT_ABANDONMENT_INTENT": "The checkout was abandoned prior to completion rather than experiencing a direct gateway rejection.",
    "POLICY_BELOW_MIN_RECOVERY_PROBABILITY": "The predicted recovery probability is below the merchant policy threshold (35%).",
    "POLICY_EXCEEDED_MAX_RECOVERY_ATTEMPTS": "The transaction has already reached the maximum allowed automated recovery attempts (2).",
    "POLICY_EXCEEDS_AUTO_ACTION_AMOUNT_LIMIT": "Transaction amount exceeds the automatic action limit (₹1,00,000) and requires manual review.",
    "STANDARD_RECOVERY_PROFILE": "Standard payment failure profile.",
}

SYSTEM_PROMPT = """You are REVORA's Revenue Recovery Explanation Agent.
Explain the supplied machine-learning recovery decision and policy evaluation to a merchant.

CRITICAL RULES:
1. Explain only the supplied structured evidence enclosed in <DATA> tags.
2. The decision, policy, and recovery probabilities are ALREADY COMPUTED and FINAL. NEVER change or recommend changing them.
3. NEVER override a POLICY_BLOCKED result or suggest bypassing safety guardrails.
4. NEVER claim money was recovered unless actual execution status is explicitly confirmed as successful.
5. Clearly distinguish EXPECTED RECOVERY (a model prediction before execution) from ACTUAL RECOVERY.
6. If evidence is insufficient, explicitly state so.
7. Use concise, professional, merchant-friendly language.
8. NEVER reveal credentials, internal tokens, or secret keys.
9. Return ONLY valid JSON adhering strictly to the required schema:
{
    "summary": "...",
    "why_this_strategy": "...",
    "expected_outcome": "...",
    "risk_note": "...",
    "merchant_action": "..."
}"""


class RecoveryExplanationAgent:
    """LLM-powered explanation agent for merchant-facing transparency with guaranteed deterministic fallbacks."""

    def __init__(self) -> None:
        self.provider = get_llm_provider()

    def _format_reason_bullets(self, reason_codes: List[str]) -> List[str]:
        return [REASON_CODE_EXPLANATIONS.get(code, f"Reason code: {code}") for code in reason_codes]

    def _generate_deterministic_explanation(
        self,
        explanation_type: str,
        context: Dict[str, Any],
        alternative_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Produce guaranteed safe, consistent, and structured deterministic explanations."""
        txn_id = context.get("transaction_id", "txn_unknown")
        amount = float(context.get("amount", 0.0))
        strategy = context.get("recommended_strategy", context.get("strategy", "NO_ACTION"))
        confidence = float(context.get("strategy_confidence", context.get("confidence", 0.0)))
        pred_prob = float(context.get("predicted_recovery_probability", 0.0))
        expected_val = float(context.get("expected_recovery_value", amount * pred_prob))
        policy_result = context.get("policy_result", "ALLOWED")
        reason_codes = context.get("reason_codes", [])
        failure_reason = context.get("failure_reason", "UNKNOWN")

        reason_bullets = self._format_reason_bullets(reason_codes)
        reasons_text = " ".join(reason_bullets) if reason_bullets else "Standard recovery analysis applied."

        if explanation_type == "DECISION":
            summary = (
                f"Revora selected {strategy} with {confidence*100:.1f}% confidence for transaction {txn_id} "
                f"(₹{amount:,.2f}), estimating a {pred_prob*100:.1f}% recovery probability."
            )
            why_strategy = (
                f"The transaction failed due to {failure_reason}. {reasons_text} "
                f"Given these signals, {strategy} provides the optimal recovery pathway."
            )
            expected_outcome = (
                f"The expected recovery value is ₹{expected_val:,.2f}. Note: This is a predictive estimate, "
                f"not confirmed recovered revenue."
            )
            risk_note = (
                "Guardrails passed successfully. Action is compliant with merchant safety thresholds."
                if policy_result == "ALLOWED"
                else f"Action is flagged as {policy_result}."
            )
            merchant_action = f"Proceed with automated {strategy} workflow."

        elif explanation_type == "WHY_NOT":
            alt = (alternative_strategy or "RETRY").upper()
            summary = f"Revora selected {strategy} over {alt} based on failure characteristics and recovery potential."
            why_strategy = (
                f"While {alt} is an available recovery option, the transaction evidence ({failure_reason}) "
                f"and reason codes ({', '.join(reason_codes)}) indicate that {strategy} has a higher expected recovery "
                f"efficiency without unnecessarily re-attempting failed channels."
            )
            expected_outcome = (
                f"{strategy} offers an estimated {pred_prob*100:.1f}% recovery probability (₹{expected_val:,.2f} expected value)."
            )
            risk_note = f"Choosing {alt} could lead to repeated failure drop-offs or customer friction."
            merchant_action = f"Maintain recommended {strategy} strategy."

        elif explanation_type == "POLICY_BLOCK":
            summary = (
                f"Revora blocked automated execution for transaction {txn_id} and defaulted to NO_ACTION "
                f"due to merchant policy constraints."
            )
            why_strategy = f"Policy enforcement triggered: {reasons_text}"
            expected_outcome = "No automated funds recovery attempt was initiated to prevent policy violation."
            risk_note = "Merchant guardrails are strictly authoritative and cannot be overridden by the AI agent."
            merchant_action = "Review transaction manually in merchant dashboard if special handling is required."

        elif explanation_type == "EXECUTION":
            exec_mode = context.get("execution_mode", "SIMULATED")
            exec_status = context.get("execution_status", "EXECUTED")
            resource_id = context.get("resource_id", "N/A")
            summary = (
                f"Revora successfully initiated {strategy} execution in {exec_mode} mode (Status: {exec_status})."
            )
            why_strategy = (
                f"The decision passed all merchant guardrail checks and dispatched {strategy}. "
                f"Resource ID: {resource_id}."
            )
            expected_outcome = (
                f"Expected recovery value is ₹{expected_val:,.2f}. "
                f"Actual recovery will only be recorded upon customer payment settlement."
            )
            risk_note = "Test Mode execution completed safely with full audit trail logging."
            merchant_action = "Monitor webhook events for subsequent payment completion."

        else:  # NO_ACTION
            summary = f"Revora determined NO_ACTION is the optimal approach for transaction {txn_id}."
            why_strategy = f"The failure context indicates low recovery utility: {reasons_text}"
            expected_outcome = f"Expected recovery value is minimal (₹{expected_val:,.2f})."
            risk_note = "Taking action on chronic failure profiles may induce merchant cost without recovery benefit."
            merchant_action = "No intervention needed."

        full_explanation = f"{summary} {why_strategy} {expected_outcome}"

        return {
            "summary": summary,
            "why_this_strategy": why_strategy,
            "expected_outcome": expected_outcome,
            "risk_note": risk_note,
            "merchant_action": merchant_action,
            "full_text": full_explanation,
        }

    def explain_decision(self, decision_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explain an ML recovery decision to a merchant."""
        return self._build_explanation("DECISION", decision_context)

    def explain_why_not_strategy(
        self, decision_context: Dict[str, Any], alternative_strategy: str
    ) -> Dict[str, Any]:
        """Explain why an alternative recovery strategy was not recommended."""
        return self._build_explanation("WHY_NOT", decision_context, alternative_strategy=alternative_strategy)

    def explain_policy_block(self, policy_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explain why policy guardrails blocked automatic execution."""
        return self._build_explanation("POLICY_BLOCK", policy_context)

    def explain_execution(self, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explain a completed or simulated recovery execution event."""
        return self._build_explanation("EXECUTION", execution_context)

    def _build_explanation(
        self,
        explanation_type: str,
        context: Dict[str, Any],
        alternative_strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sanitize inputs, invoke LLM provider if configured, or return deterministic fallback."""
        # Sanitize context: STRICTLY strip all sensitive/private credentials
        sanitized_context = {
            k: v
            for k, v in context.items()
            if not any(sub in k.lower() for sub in ["secret", "key", "password", "token", "auth"])
        }

        # Generate deterministic fallback first as safety baseline
        fallback_data = self._generate_deterministic_explanation(
            explanation_type, sanitized_context, alternative_strategy
        )

        provider_name = settings.LLM_PROVIDER
        model_name = settings.LLM_MODEL
        fallback_used = True
        structured_content = fallback_data

        # If an external LLM is configured, attempt generation
        if provider_name.lower() not in ["deterministic", "none", ""] and settings.LLM_API_KEY:
            prompt = (
                f"Explanation Type: {explanation_type}\n"
                f"Alternative Strategy Requested: {alternative_strategy or 'None'}\n"
                f"<DATA>\n{json.dumps(sanitized_context, indent=2)}\n</DATA>\n"
                f"Produce concise structured JSON explaining this decision."
            )
            try:
                raw_response = self.provider.generate(prompt, system_instruction=SYSTEM_PROMPT)
                if raw_response:
                    parsed = json.loads(raw_response)
                    if all(k in parsed for k in ["summary", "why_this_strategy", "expected_outcome"]):
                        structured_content = {
                            "summary": str(parsed.get("summary", fallback_data["summary"])),
                            "why_this_strategy": str(parsed.get("why_this_strategy", fallback_data["why_this_strategy"])),
                            "expected_outcome": str(parsed.get("expected_outcome", fallback_data["expected_outcome"])),
                            "risk_note": str(parsed.get("risk_note", fallback_data["risk_note"])),
                            "merchant_action": str(parsed.get("merchant_action", fallback_data["merchant_action"])),
                            "full_text": f"{parsed.get('summary', '')} {parsed.get('why_this_strategy', '')} {parsed.get('expected_outcome', '')}".strip(),
                        }
                        fallback_used = False
            except Exception as e:
                logger.warning("LLM response parse failure: %s. Using deterministic fallback.", type(e).__name__)
                fallback_used = True

        txn_id = sanitized_context.get("transaction_id", "txn_unknown")
        strategy = sanitized_context.get("recommended_strategy", sanitized_context.get("strategy", "NO_ACTION"))
        confidence = float(sanitized_context.get("strategy_confidence", sanitized_context.get("confidence", 0.0)))
        pred_prob = float(sanitized_context.get("predicted_recovery_probability", 0.0))
        expected_val = float(sanitized_context.get("expected_recovery_value", 0.0))

        audit_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_id": txn_id,
            "explanation_type": explanation_type,
            "strategy": strategy,
            "policy_result": sanitized_context.get("policy_result", "ALLOWED"),
            "provider": provider_name if not fallback_used else "deterministic_fallback",
            "model": model_name if not fallback_used else "rule_engine",
            "fallback_used": fallback_used,
        }

        return {
            "transaction_id": txn_id,
            "type": explanation_type,
            "strategy": strategy,
            "explanation": structured_content["full_text"],
            "structured_explanation": structured_content,
            "evidence": {
                "confidence": confidence,
                "predicted_recovery_probability": pred_prob,
                "expected_recovery_value": expected_val,
                "reason_codes": sanitized_context.get("reason_codes", []),
            },
            "provider": provider_name if not fallback_used else "deterministic_fallback",
            "model": model_name if not fallback_used else "rule_engine",
            "fallback_used": fallback_used,
            "audit_event": audit_event,
        }


explanation_agent = RecoveryExplanationAgent()
