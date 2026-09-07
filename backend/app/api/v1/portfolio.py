from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import PortfolioRun, PortfolioAllocation, Vendor
from app.api.v1.quantum import run_quantum_optimization_impl
from app.schemas.dto import QuantumPortfolioRequest
from app.core.security import require_roles
from app.core.rate_limit import limiter

router = APIRouter()


@router.post("/create")
@limiter.limit("10/minute")
def create_portfolio(
    request: Request,
    payload: QuantumPortfolioRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    q_res = run_quantum_optimization_impl(payload, db=db, current_user=current_user)

    portfolio = PortfolioRun(
        lender_id=current_user.id,
        available_capital=payload.available_capital,
        risk_limit=payload.max_risk_tolerance,
        objective_value=q_res.objective_value,
        selected_vendor_count=len(q_res.selected_vendors),
        allocated_capital=q_res.allocated_capital,
        quantum_run_id=q_res.run_id,
        status="COMPLETED"
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    # Persist the EXACT per-vendor numbers from this optimization run
    # (q_res.allocations), not separately hardcoded placeholders - so the
    # stored portfolio can never disagree with what the quantum solver
    # actually computed. Falls back to a neutral default only for a vendor
    # that is somehow missing from the run's allocation detail (should not
    # normally happen; kept only so a single bad record can't 500 the request).
    allocations_by_vendor = {a["vendor_id"]: a for a in (q_res.allocations or [])}
    for v_id in q_res.selected_vendors:
        a = allocations_by_vendor.get(v_id, {})
        alloc = PortfolioAllocation(
            portfolio_id=portfolio.portfolio_id,
            vendor_id=v_id,
            requested_amount=a.get("requested_amount", 0.0),
            allocated_amount=a.get("allocated_amount", 0.0),
            predicted_risk=a.get("predicted_risk", 0.0),
            expected_return=a.get("expected_return", 0.0),
            selected=True
        )
        db.add(alloc)

    db.commit()
    return {"portfolio_id": portfolio.portfolio_id, "status": "COMPLETED", "selected_count": portfolio.selected_vendor_count}


@router.get("/{portfolio_id}")
def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    portfolio = db.query(PortfolioRun).filter(PortfolioRun.portfolio_id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio run not found")
    return portfolio
