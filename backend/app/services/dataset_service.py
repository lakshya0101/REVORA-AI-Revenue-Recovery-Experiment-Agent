import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.synthetic_data_generator import generate_synthetic_cases, save_cases_to_csv

# Resolve data path relative to backend or project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CSV_PATH = DATA_DIR / "revenue_recovery_cases.csv"


class DatasetService:
    """Service to generate, load, and analyze the revenue recovery dataset."""

    def __init__(self, csv_path: Path = CSV_PATH) -> None:
        self.csv_path = csv_path

    def ensure_dataset(self, count: int = 1000, seed: int = 42) -> Path:
        """Ensure the CSV file exists, generating it if missing."""
        if not self.csv_path.exists():
            return self.regenerate_dataset(count=count, seed=seed)
        return self.csv_path

    def regenerate_dataset(self, count: int = 1000, seed: int = 42) -> Path:
        """Regenerate the dataset using a fixed random seed."""
        cases = generate_synthetic_cases(count=count, seed=seed)
        return save_cases_to_csv(cases, self.csv_path)

    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load and parse records from the CSV file."""
        self.ensure_dataset()
        cases: List[Dict[str, Any]] = []

        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cases.append({
                    "transaction_id": row["transaction_id"],
                    "customer_id": row["customer_id"],
                    "order_id": row["order_id"],
                    "amount": float(row["amount"]),
                    "currency": row["currency"],
                    "payment_status": row["payment_status"],
                    "failure_reason": row["failure_reason"],
                    "customer_type": row["customer_type"],
                    "previous_successful_payments": int(row["previous_successful_payments"]),
                    "previous_failed_payments": int(row["previous_failed_payments"]),
                    "previous_recovery_attempts": int(row["previous_recovery_attempts"]),
                    "historical_recovery_rate": float(row["historical_recovery_rate"]),
                    "customer_lifetime_value": float(row["customer_lifetime_value"]),
                    "time_since_failure_minutes": int(row["time_since_failure_minutes"]),
                    "payment_method": row["payment_method"],
                    "checkout_abandoned": row["checkout_abandoned"].lower() == "true",
                    "order_value_segment": row["order_value_segment"],
                    "ground_truth_best_strategy": row["ground_truth_best_strategy"],
                    "ground_truth_recovery_probability": float(row["ground_truth_recovery_probability"]),
                    "ground_truth_recovered": row["ground_truth_recovered"].lower() == "true",
                    "ground_truth_recovered_amount": float(row["ground_truth_recovered_amount"]),
                })

        return cases

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Calculate statistical summaries and distributions of the dataset."""
        cases = self.load_dataset()
        total_cases = len(cases)

        if total_cases == 0:
            return {
                "total_cases": 0,
                "total_revenue_at_risk": 0.0,
                "recoverable_revenue": 0.0,
                "historical_recovery_rate": 0.0,
                "strategy_distribution": {},
                "failure_reason_distribution": {},
                "customer_type_distribution": {},
                "order_value_segment_distribution": {},
            }

        total_revenue_at_risk = round(sum(c["amount"] for c in cases), 2)
        recoverable_revenue = round(sum(c["ground_truth_recovered_amount"] for c in cases), 2)
        total_recovered_cases = sum(1 for c in cases if c["ground_truth_recovered"])
        recovery_rate = round(total_recovered_cases / total_cases, 4)

        strategy_distribution: Dict[str, int] = {}
        failure_reason_distribution: Dict[str, int] = {}
        customer_type_distribution: Dict[str, int] = {}
        order_value_segment_distribution: Dict[str, int] = {}

        for c in cases:
            strat = c["ground_truth_best_strategy"]
            strategy_distribution[strat] = strategy_distribution.get(strat, 0) + 1

            reason = c["failure_reason"]
            failure_reason_distribution[reason] = failure_reason_distribution.get(reason, 0) + 1

            cust_type = c["customer_type"]
            customer_type_distribution[cust_type] = customer_type_distribution.get(cust_type, 0) + 1

            segment = c["order_value_segment"]
            order_value_segment_distribution[segment] = order_value_segment_distribution.get(segment, 0) + 1

        return {
            "total_cases": total_cases,
            "total_revenue_at_risk": total_revenue_at_risk,
            "recoverable_revenue": recoverable_revenue,
            "historical_recovery_rate": recovery_rate,
            "strategy_distribution": strategy_distribution,
            "failure_reason_distribution": failure_reason_distribution,
            "customer_type_distribution": customer_type_distribution,
            "order_value_segment_distribution": order_value_segment_distribution,
        }


dataset_service = DatasetService()
