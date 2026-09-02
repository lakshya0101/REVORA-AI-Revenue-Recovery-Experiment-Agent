import logging
from typing import Any, Dict, Optional
import razorpay
from razorpay.errors import BadRequestError, GatewayError, ServerError, SignatureVerificationError

from app.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    """Service class for interacting with Razorpay API in Test Mode."""

    def get_client(self) -> Optional[razorpay.Client]:
        """Dynamically create or return Razorpay Client based on current settings."""
        key_id = settings.razorpay_key_id.strip()
        key_secret = settings.razorpay_key_secret.strip()

        if not key_id or not key_secret:
            return None

        try:
            return razorpay.Client(auth=(key_id, key_secret))
        except Exception as e:
            logger.error("Failed to initialize Razorpay Client: %s", type(e).__name__)
            return None

    @property
    def is_configured(self) -> bool:
        """Check if Razorpay API keys are configured."""
        return bool(settings.razorpay_key_id.strip() and settings.razorpay_key_secret.strip())

    def list_orders(self, count: int = 10, skip: int = 0) -> Dict[str, Any]:
        """Fetch list of orders from Razorpay Test Mode."""
        client = self.get_client()
        if not client:
            raise ValueError("Razorpay credentials are not configured or incomplete in .env.")

        try:
            orders = client.order.all({"count": count, "skip": skip})
            items = orders.get("items", []) if isinstance(orders, dict) else []
            total_count = orders.get("count", len(items)) if isinstance(orders, dict) else len(items)
            return {
                "count": total_count,
                "items": items,
            }
        except (BadRequestError, GatewayError, ServerError, SignatureVerificationError) as rz_err:
            logger.error("Razorpay API error encountered: %s", type(rz_err).__name__)
            raise RuntimeError(f"Razorpay API error: {type(rz_err).__name__}")
        except Exception as err:
            logger.error("Unexpected error connecting to Razorpay: %s", type(err).__name__)
            raise RuntimeError("Failed to communicate with Razorpay API.")

    def test_connection(self) -> Dict[str, Any]:
        """Verify authentication with Razorpay by fetching recent orders."""
        if not self.is_configured:
            return {
                "connected": False,
                "message": "Razorpay API credentials are not set in .env",
                "orders_count": 0,
            }

        try:
            orders_data = self.list_orders(count=1)
            return {
                "connected": True,
                "message": "Successfully connected to Razorpay Test Mode",
                "orders_count": orders_data.get("count", 0),
            }
        except Exception as e:
            return {
                "connected": False,
                "message": f"Connection failed: {str(e)}",
                "orders_count": 0,
            }

    def get_payment_link_status(self, payment_link_id: str) -> Dict[str, Any]:
        """Fetch status of an existing Razorpay Payment Link in Test Mode. Safe READ-ONLY operation."""
        client = self.get_client()
        if not client:
            return {
                "success": False,
                "error": "Razorpay client not configured",
            }

        try:
            link = client.payment_link.fetch(payment_link_id)
            return {
                "success": True,
                "payment_link_id": link.get("id"),
                "status": link.get("status"),  # created, paid, partially_paid, expired, cancelled
                "amount": float(link.get("amount", 0)) / 100.0,
                "amount_paid": float(link.get("amount_paid", 0)) / 100.0,
                "reference_id": link.get("reference_id"),
                "short_url": link.get("short_url"),
            }
        except Exception as e:
            logger.error("Failed to fetch Razorpay Payment Link status: %s", type(e).__name__)
            return {
                "success": False,
                "error": f"Failed to retrieve payment link: {type(e).__name__}",
                "payment_link_id": payment_link_id,
            }


razorpay_service = RazorpayService()
