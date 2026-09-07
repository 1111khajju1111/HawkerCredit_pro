from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Vendor, CreditScore, Loan, User
from app.schemas.dto import VendorCreate, VendorResponse
from app.core.security import verify_vendor_access, require_roles, get_current_user

router = APIRouter()


def _vendor_discovery_payload(vendor: Vendor) -> dict:
    """Build one lender-facing vendor card from persisted vendor intelligence."""
    score = vendor.credit_score
    requested = next(
        (loan.principal for loan in sorted(vendor.loans, key=lambda x: x.created_at or vendor.created_at)
         if loan.repayment_status in {"REQUESTED", "UNDER_REVIEW"}),
        None,
    )
    if requested is None and vendor.loans:
        requested = max((loan.principal for loan in vendor.loans), default=None)
    return {
        "vendor_id": vendor.vendor_id,
        "user_id": vendor.user_id,
        "name": vendor.name,
        "phone": vendor.phone,
        "business_type": vendor.business_type,
        "business_description": vendor.business_description,
        "location": vendor.location,
        "operating_since": vendor.operating_since,
        "registration_status": vendor.registration_status,
        "operating_days": vendor.operating_days,
        "created_at": vendor.created_at,
        "score": score.score if score else None,
        "risk_category": score.risk_category if score else None,
        "repayment_probability": score.repayment_probability if score else None,
        "data_quality_score": vendor.credit_feature.data_quality_score if vendor.credit_feature else None,
        "requested_loan": requested,
        "pending_human_review": any(
            loan.repayment_status in {"REQUESTED", "UNDER_REVIEW"} for loan in vendor.loans
        ),
    }


@router.get("", response_model=List[VendorResponse])
def list_vendors(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    """Lender/admin vendor discovery with persisted credit intelligence."""
    vendors = db.query(Vendor).order_by(Vendor.created_at.asc()).all()
    return [_vendor_discovery_payload(v) for v in vendors]


@router.get("/lender-summary")
def lender_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    """Dashboard summary backed by the same persisted demo/vendor data."""
    vendors = db.query(Vendor).all()
    scores = [v.credit_score.score for v in vendors if v.credit_score and v.credit_score.score is not None]
    pending = [
        loan for loan in db.query(Loan).all()
        if loan.repayment_status in {"REQUESTED", "UNDER_REVIEW"}
    ]
    return {
        "total_vendors": len(vendors),
        "avg_credit_score": round(sum(scores) / len(scores), 2) if scores else None,
        "pending_human_reviews": len(pending),
        "vendors": [_vendor_discovery_payload(v) for v in vendors[:12]],
        "synthetic_demo": True,
        "demo_dataset": {"vendors_target": 100, "lenders_target": 10},
    }


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("", response_model=VendorResponse)
def create_vendor(
    vendor_in: VendorCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="A vendor profile already exists for this user")

    vendor = Vendor(
        user_id=current_user.id,
        name=vendor_in.name,
        phone=vendor_in.phone,
        business_type=vendor_in.business_type,
        business_description=vendor_in.business_description,
        location=vendor_in.location,
        operating_since=vendor_in.operating_since,
        operating_days=vendor_in.operating_days
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor
