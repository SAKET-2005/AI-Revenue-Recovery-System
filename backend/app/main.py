"""
ReviveAI — FastAPI Application Entry Point.

AI-powered revenue recovery command center.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.ml.predictor import predictor

from app.api.dashboard import router as dashboard_router
from app.api.transactions import router as transactions_router
from app.api.recovery import router as recovery_router
from app.api.webhooks import router as webhooks_router
from app.api.audit import router as audit_router
from app.api.evaluation import router as evaluation_router
from app.api.ml_routes import router as ml_router
from app.api.payment_links import router as payment_links_router
from app.api.demo import router as demo_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("=" * 60)
    print("  ReviveAI — Revenue Recovery Agent")
    print("=" * 60)
    print(f"  Mode: {'DEMO' if settings.is_demo_mode else 'LIVE'}")
    print(f"  LLM:  {'Available' if settings.has_llm else 'Fallback (deterministic)'}")
    print(f"  Razorpay: {'Test Mode' if settings.has_razorpay else 'Simulation'}")
    print("=" * 60)

    # Initialize database
    await init_db()
    print("[DB] Database initialized")

    # Load ML model
    if predictor.load():
        print(f"[ML] Model loaded: {predictor.metrics.get('model_version', 'unknown')}")
        print(f"[ML] ROC-AUC: {predictor.metrics.get('roc_auc', 'N/A')}")
    else:
        print("[ML] Model not found — using heuristic fallback")
        print("[ML] Run 'python -m scripts.train_model' to train")

    yield

    # Shutdown
    print("[App] Shutting down")


app = FastAPI(
    title="ReviveAI",
    description="AI-powered revenue recovery command center for merchants",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dashboard_router)
app.include_router(transactions_router)
app.include_router(recovery_router)
app.include_router(webhooks_router)
app.include_router(audit_router)
app.include_router(evaluation_router)
app.include_router(ml_router)
app.include_router(payment_links_router)
app.include_router(demo_router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "mode": "demo" if settings.is_demo_mode else "live",
        "llm_available": settings.has_llm,
        "razorpay_available": settings.has_razorpay,
        "ml_model_loaded": predictor.is_loaded,
        "database": "connected",
        "version": "1.0.0",
    }
