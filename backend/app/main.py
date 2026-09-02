from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Revenue Recovery Experiment Agent for Razorpay AI Buildathon 2026",
    version="0.1.0",
)

# CORS configuration (permissive for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "name": "Revora",
        "description": "AI Revenue Recovery Experiment Agent",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# Include Routers
from app.routes.razorpay import router as razorpay_router
from app.routes.dataset import router as dataset_router
from app.routes.recovery import router as recovery_router
from app.routes.experiments import router as experiments_router
from app.routes.execution import router as execution_router
from app.routes.explanations import router as explanations_router

app.include_router(razorpay_router)
app.include_router(dataset_router)
app.include_router(recovery_router)
app.include_router(experiments_router)
app.include_router(execution_router)
app.include_router(explanations_router)






