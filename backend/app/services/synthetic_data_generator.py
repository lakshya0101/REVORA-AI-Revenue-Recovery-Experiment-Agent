import csv
from pathlib import Path
import random
from typing import Any, Dict, List

# Supported Strategies
STRATEGIES = ["RETRY", "PAYMENT_LINK", "ALTERNATE_FLOW", "NO_ACTION"]

# Failure Reasons with primary baseline characteristics
FAILURE_REASONS = [
    "BANK_SERVER_DOWN",
    "NETWORK_TIMEOUT",
    "INSUFFICIENT_FUNDS",
    "EXPIRED_CARD",
    "INCORRECT_OTP",
    "CHECKOUT_DROPOFF",
    "UPI_APP_UNRESPONSIVE",
    "TRANSACTION_LIMIT_EXCEEDED",
    "CARD_AUTHENTICATION_FAILED",
    "GATEWAY_REJECTED",
]

PAYMENT_METHODS = ["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING", "WALLET"]
CUSTOMER_TYPES = ["FIRST_TIME", "RETURNING", "ENTERPRISE", "VIP"]


def determine_value_segment(amount: float) -> str:
    if amount < 500:
        return "MICRO"
    elif amount < 2500:
        return "LOW"
    elif amount < 10000:
        return "MEDIUM"
    elif amount < 50000:
        return "HIGH"
    else:
        return "ENTERPRISE"


def generate_synthetic_cases(count: int = 1000, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate a reproducible synthetic dataset of revenue recovery cases."""
    random.seed(seed)
    cases: List[Dict[str, Any]] = []

    for i in range(1, count + 1):
        case_id_str = f"{i:04d}"
        transaction_id = f"txn_syn_{case_id_str}"
        customer_id = f"cust_syn_{random.randint(100, 999)}"
        order_id = f"order_syn_{case_id_str}"

        # Customer demographics & history
        customer_type = random.choices(
            CUSTOMER_TYPES, weights=[0.40, 0.45, 0.10, 0.05], k=1
        )[0]

        if customer_type == "FIRST_TIME":
            previous_successful_payments = 0
            previous_failed_payments = random.choices([0, 1, 2], weights=[0.8, 0.15, 0.05], k=1)[0]
            previous_recovery_attempts = 0
            historical_recovery_rate = 0.0
            clv = round(random.uniform(0.0, 500.0), 2)
        else:
            previous_successful_payments = random.randint(1, 40)
            previous_failed_payments = random.randint(0, 8)
            previous_recovery_attempts = random.randint(0, min(previous_failed_payments, 5))
            if previous_recovery_attempts > 0:
                recovered_count = random.randint(0, previous_recovery_attempts)
                historical_recovery_rate = round(recovered_count / previous_recovery_attempts, 2)
            else:
                historical_recovery_rate = round(random.uniform(0.3, 0.9), 2)
            
            clv_multiplier = 1.0 if customer_type == "RETURNING" else (3.0 if customer_type == "VIP" else 6.0)
            clv = round(random.uniform(2000.0, 50000.0) * clv_multiplier, 2)

        # Amount distribution (weighted towards realistic e-commerce & SaaS ticket sizes)
        amount_bracket = random.choices(["micro", "mid", "high", "enterprise"], weights=[0.35, 0.45, 0.15, 0.05], k=1)[0]
        if amount_bracket == "micro":
            amount = round(random.uniform(99.0, 999.0), 2)
        elif amount_bracket == "mid":
            amount = round(random.uniform(1000.0, 9999.0), 2)
        elif amount_bracket == "high":
            amount = round(random.uniform(10000.0, 49999.0), 2)
        else:
            amount = round(random.uniform(50000.0, 185000.0), 2)

        currency = "INR"
        order_value_segment = determine_value_segment(amount)
        payment_method = random.choices(PAYMENT_METHODS, weights=[0.45, 0.25, 0.15, 0.10, 0.05], k=1)[0]

        # Failure context
        failure_reason = random.choices(FAILURE_REASONS, weights=[0.18, 0.14, 0.12, 0.08, 0.10, 0.15, 0.10, 0.05, 0.05, 0.03], k=1)[0]
        checkout_abandoned = (failure_reason == "CHECKOUT_DROPOFF") or (random.random() < 0.05)
        payment_status = "ABANDONED" if checkout_abandoned else "FAILED"
        time_since_failure_minutes = random.randint(2, 2880)  # Between 2 mins and 48 hours

        # Probabilistic Simulation for Ground Truth Strategy & Probability
        # Base probabilities for strategies
        scores = {"RETRY": 0.25, "PAYMENT_LINK": 0.25, "ALTERNATE_FLOW": 0.25, "NO_ACTION": 0.25}

        # Context rules adjusting strategy scores
        if failure_reason in ["BANK_SERVER_DOWN", "NETWORK_TIMEOUT", "GATEWAY_REJECTED"]:
            scores["RETRY"] += 0.50
            scores["PAYMENT_LINK"] += 0.10
        elif failure_reason in ["CHECKOUT_DROPOFF", "INCORRECT_OTP"]:
            scores["PAYMENT_LINK"] += 0.55
            scores["RETRY"] -= 0.10
        elif failure_reason in ["EXPIRED_CARD", "UPI_APP_UNRESPONSIVE", "CARD_AUTHENTICATION_FAILED"]:
            scores["ALTERNATE_FLOW"] += 0.50
            scores["PAYMENT_LINK"] += 0.20
        elif failure_reason in ["INSUFFICIENT_FUNDS", "TRANSACTION_LIMIT_EXCEEDED"]:
            if customer_type in ["ENTERPRISE", "VIP", "RETURNING"] and historical_recovery_rate > 0.4:
                scores["PAYMENT_LINK"] += 0.35
                scores["ALTERNATE_FLOW"] += 0.25
            else:
                scores["NO_ACTION"] += 0.40

        # Adjust based on time since failure
        if time_since_failure_minutes > 1440:  # > 24 hours
            scores["RETRY"] -= 0.25
            scores["PAYMENT_LINK"] += 0.20
            scores["NO_ACTION"] += 0.15

        # Adjust based on prior failed payments / recovery attempts
        if previous_failed_payments >= 5 and historical_recovery_rate < 0.2:
            scores["NO_ACTION"] += 0.45

        # Add slight stochastic noise so rules aren't purely deterministic
        for s in scores:
            scores[s] = max(0.01, scores[s] + random.uniform(-0.10, 0.10))

        # Select best strategy from highest score
        best_strategy = max(scores, key=scores.get)

        # Calculate ground truth recovery probability (between 0.05 and 0.95)
        base_prob = 0.50
        if best_strategy == "RETRY":
            base_prob = 0.68 if failure_reason in ["BANK_SERVER_DOWN", "NETWORK_TIMEOUT"] else 0.45
        elif best_strategy == "PAYMENT_LINK":
            base_prob = 0.72 if checkout_abandoned or customer_type in ["VIP", "RETURNING"] else 0.52
        elif best_strategy == "ALTERNATE_FLOW":
            base_prob = 0.64 if payment_method in ["UPI", "CREDIT_CARD"] else 0.48
        elif best_strategy == "NO_ACTION":
            base_prob = 0.08

        # Modulate with customer history
        if customer_type in ["VIP", "ENTERPRISE"]:
            base_prob += 0.15
        elif customer_type == "RETURNING":
            base_prob += 0.08 * (historical_recovery_rate - 0.5)
        else:
            base_prob -= 0.05

        # Modulate with elapsed time
        if time_since_failure_minutes < 30:
            base_prob += 0.10
        elif time_since_failure_minutes > 720:
            base_prob -= 0.15

        # Modulate with amount (very high amounts get slightly more manual customer attention)
        if order_value_segment == "ENTERPRISE":
            base_prob += 0.05

        recovery_probability = max(0.02, min(0.96, round(base_prob + random.uniform(-0.12, 0.12), 4)))

        # Simulate outcome based on recovery_probability
        recovered = random.random() < recovery_probability
        recovered_amount = amount if recovered else 0.0

        cases.append({
            "transaction_id": transaction_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_status": payment_status,
            "failure_reason": failure_reason,
            "customer_type": customer_type,
            "previous_successful_payments": previous_successful_payments,
            "previous_failed_payments": previous_failed_payments,
            "previous_recovery_attempts": previous_recovery_attempts,
            "historical_recovery_rate": historical_recovery_rate,
            "customer_lifetime_value": clv,
            "time_since_failure_minutes": time_since_failure_minutes,
            "payment_method": payment_method,
            "checkout_abandoned": checkout_abandoned,
            "order_value_segment": order_value_segment,
            "ground_truth_best_strategy": best_strategy,
            "ground_truth_recovery_probability": recovery_probability,
            "ground_truth_recovered": recovered,
            "ground_truth_recovered_amount": recovered_amount,
        })

    return cases


def save_cases_to_csv(cases: List[Dict[str, Any]], file_path: Path) -> Path:
    """Save generated cases to a CSV file."""
    if not cases:
        raise ValueError("Cases list is empty.")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(cases[0].keys())

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cases)

    return file_path
