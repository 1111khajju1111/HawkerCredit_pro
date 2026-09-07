from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Loan, AuditLog, Vendor
from app.schemas.dto import LoanCreate, LoanResponse, HumanUnderwriteRequest
from app.core.security import verify_vendor_access, require_roles
from app.core.rate_limit import limiter

router = APIRouter()


@router.post("", response_model=LoanResponse)
@limiter.limit("30/minute")
def request_loan(
    request: Request,
    vendor_id: str,
    loan_in: LoanCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    due_date = datetime.utcnow() + timedelta(days=loan_in.due_months * 30)
    loan = Loan(
        vendor_id=vendor_id,
        principal=loan_in.principal,
        interest_rate=loan_in.interest_rate,
        due_date=due_date,
        repayment_status="REQUESTED"
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    db.add(AuditLog(user_id=vendor_id, action="LOAN_REQUESTED", resource_type="LOAN", resource_id=loan.loan_id))
    db.commit()

    return loan


@router.get("/vendor/{vendor_id}", response_model=List[LoanResponse])
def get_vendor_loans(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    return db.query(Loan).filter(Loan.vendor_id == vendor_id).all()


@router.get("", response_model=List[LoanResponse])
def list_all_loans(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    return db.query(Loan).all()


@router.post("/underwrite")
@limiter.limit("30/minute")
def human_underwrite(
    request: Request,
    payload: HumanUnderwriteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    loan = db.query(Loan).filter(Loan.loan_id == payload.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    loan.repayment_status = payload.decision
    loan.human_notes = payload.notes
    loan.lender_id = current_user.id
    loan.human_decision_at = datetime.utcnow()

    vendor = db.query(Vendor).filter(Vendor.vendor_id == loan.vendor_id).first()
    credit_score_at_decision = vendor.credit_score if vendor else None
    db.add(AuditLog(
        user_id=current_user.id,
        action=f"HUMAN_UNDERWRITE_{payload.decision}",
        resource_type="LOAN",
        resource_id=loan.loan_id,
        metadata_json={
            "vendor_id": loan.vendor_id,
            "notes": payload.notes,
            "credit_score_at_decision": credit_score_at_decision.score if credit_score_at_decision else None,
            "risk_category_at_decision": credit_score_at_decision.risk_category if credit_score_at_decision else None,
            "model_version_at_decision": credit_score_at_decision.model_version if credit_score_at_decision else None,
        }
    ))
    db.commit()
    return {"message": f"Loan decision recorded as {payload.decision}", "loan_id": loan.loan_id}
