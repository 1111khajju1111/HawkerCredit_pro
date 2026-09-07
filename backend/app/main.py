import os
from contextlib import asynccontextmanager
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
from app.demo_seed import ensure_demo_dataset
from app.api.v1 import (
    auth, vendors, transactions, expenses, inventory,
    loans, ai, credit, quantum, portfolio, consent, audit, admin
)

# Table creation is fast and synchronous - fine to run at import time,
# well before the slow work below.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # IMPORTANT: this runs AFTER uvicorn has already bound the port and
    # started accepting TCP connections, but BEFORE the app serves any
    # HTTP requests. Model registration (which may train a fresh model on
    # a completely cold deploy) and demo-data seeding (creating 100
    # vendors with credit scoring + SHAP explanations - a few seconds on
    # a normal machine, but can take much longer on a throttled free-tier
    # CPU) both used to run at MODULE IMPORT TIME, before uvicorn could
    # bind the port at all. On a slow host that meant the port never
    # opened within the platform's health-check window, and the deploy
    # was killed even though the app would have started fine given more
    # time. Moving this work here means the port opens immediately;
    # requests that arrive before startup finishes will simply wait
    # rather than the whole deploy being torn down.
    try:
        with SessionLocal() as _startup_db:
            register_persisted_model(_startup_db)
    except Exception as _startup_error:
        print(f"Startup model registration warning: {_startup_error}")

    if os.getenv("DEMO_SEED_ON_STARTUP", "true").lower() in {"1", "true", "yes"}:
        try:
            ensure_demo_dataset()
        except Exception as _demo_seed_error:
            print(f"Startup demo-data seeding warning: {_demo_seed_error}")

    yield
    # (no shutdown work needed)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
