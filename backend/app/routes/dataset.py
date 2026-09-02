from typing import Optional
from fastapi import APIRouter, Query

from app.services.dataset_service import dataset_service

router = APIRouter(prefix="/api/dataset", tags=["Dataset"])


@router.get("/stats")
def get_dataset_statistics():
    """Return safe aggregate statistics for the revenue recovery dataset."""
    return dataset_service.get_dataset_stats()


@router.post("/regenerate")
def regenerate_dataset(
    count: int = Query(default=1000, ge=100, le=10000, description="Number of synthetic cases"),
    seed: int = Query(default=42, description="Random seed for reproducibility"),
):
    """Regenerate the synthetic dataset using the deterministic seed."""
    dataset_service.regenerate_dataset(count=count, seed=seed)
    return {
        "status": "success",
        "message": f"Successfully regenerated {count} synthetic cases with seed {seed}.",
        "stats": dataset_service.get_dataset_stats(),
    }
