from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.services.razorpay_service import razorpay_service

router = APIRouter(prefix="/api/razorpay", tags=["Razorpay"])


@router.get("/test")
def test_razorpay_connection():
    """Test Razorpay Test Mode authentication and connectivity securely."""
    result = razorpay_service.test_connection()

    if not result.get("connected"):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY
            if "API error" in result.get("message", "")
            else status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result,
        )

    return result
