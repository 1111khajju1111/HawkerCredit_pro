import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.database import engine, Base, get_db, SessionLocal
from app.ai.model_registry import register_persisted_model

# Schema management is handled by Alembic before application startup.
try:
    from alembic import command
    from alembic.config import Config as AlembicConfig
    _alembic_cfg = AlembicConfig(os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini"))
    command.upgrade(_alembic_cfg, "head")
except Exception as _migration_error:
    if settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError(f"Database migration failed in production: {_migration_error}") from _migration_error
    print(f"Startup migration warning: {_migration_error}")
from app.demo_seed import ensure_demo_dataset
from app.api.v1 import (
    auth, vendors, transactions, expenses, inventory,
    loans, ai, credit, quantum, portfolio, consent, audit, admin
)

# Initialize database tables and register the persisted credit model.
try:
    with SessionLocal() as _startup_db:
        register_persisted_model(_startup_db)
except Exception as _startup_error:
    # The API must still start if model registration is temporarily unavailable.
    print(f"Startup model registration warning: {_startup_error}")

# Demo environments can opt into an idempotent synthetic dataset on startup.
# This never clears existing rows. Enabled by default in the production-demo bundle; set DEMO_SEED_ON_STARTUP=false for a clean non-demo deployment.
if os.getenv("DEMO_SEED_ON_STARTUP", "false").lower() in {"1", "true", "yes"}:
    try:
        ensure_demo_dataset()
    except Exception as _demo_seed_error:
        # A seeding problem must not hide the model-registration result or
        # prevent the API from starting; the failure remains visible in logs.
        print(f"Startup demo-data seeding warning: {_demo_seed_error}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Rate limiting protects authentication and resource-intensive financial/quantum endpoints.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(vendors.router, prefix=f"{settings.API_V1_STR}/vendors", tags=["Vendors"])
app.include_router(transactions.router, prefix=f"{settings.API_V1_STR}/transactions", tags=["Transactions"])
app.include_router(expenses.router, prefix=f"{settings.API_V1_STR}/expenses", tags=["Expenses"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["Inventory"])
app.include_router(loans.router, prefix=f"{settings.API_V1_STR}/loans", tags=["Loans"])
app.include_router(ai.router, prefix=f"{settings.API_V1_STR}/ai", tags=["AI Intelligence"])
app.include_router(credit.router, prefix=f"{settings.API_V1_STR}/credit-score", tags=["Credit Intelligence Score"])
app.include_router(quantum.router, prefix=f"{settings.API_V1_STR}/quantum", tags=["Quantum Optimization"])
app.include_router(portfolio.router, prefix=f"{settings.API_V1_STR}/portfolio", tags=["Portfolio"])
app.include_router(consent.router, prefix=f"{settings.API_V1_STR}/consent", tags=["Consent Management"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit-logs", tags=["Audit Logging"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin & Model Monitoring"])

# Health Check Endpoints
@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "HEALTHY", "database": "CONNECTED"}
    except Exception as e:
        return {"status": "UNHEALTHY", "error": str(e)}

@app.get("/ai/health")
def ai_health():
    return {"status": "HEALTHY", "model_engine": "Scikit-Learn Random Forest Pipeline v1.2.0"}

@app.get("/quantum/health")
def quantum_health():
    return {"status": "HEALTHY", "backend": "Qiskit Aer Simulator / QAOA QUBO Solver"}
