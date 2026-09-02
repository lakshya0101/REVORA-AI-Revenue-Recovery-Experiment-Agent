from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.experiment_engine import experiment_engine, experiment_store

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


class RunExperimentRequest(BaseModel):
    sample_size: int = Field(default=100, ge=10, le=1000, description="Number of cases to sample for experiment")
    seed: Optional[int] = Field(default=42, description="Random seed for sample reproducibility")


@router.post("/run")
def run_experiment_endpoint(req: RunExperimentRequest):
    """Run an autonomous recovery experiment comparing Revora against the baseline strategy."""
    return experiment_engine.run_experiment(sample_size=req.sample_size, seed=req.seed or 42)


@router.get("")
def list_experiments():
    """Retrieve history of all executed experiments."""
    return experiment_store.list_experiments()


@router.get("/{experiment_id}")
def get_experiment_by_id(experiment_id: str):
    """Retrieve details and audit metrics for a specific experiment."""
    exp = experiment_store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )
    return exp
