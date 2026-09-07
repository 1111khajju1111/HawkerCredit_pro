from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import ConsentRecord, AuditLog, Vendor
from app.core.security import verify_vendor_access, get_current_user

router = APIRouter()


@router.get("/{vendor_id}")
def get_vendor_consents(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    consents = db.query(ConsentRecord).filter(ConsentRecord.vendor_id == vendor_id).all()
    # Viewing consent settings must never grant consent. New vendor accounts
    # receive explicit records during registration/demo seeding; for legacy
    # vendors with no record, return an empty list instead of granting consent.
    return consents


@router.post("/toggle")
def toggle_consent(
    consent_id: str,
    granted: bool,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(ConsentRecord).filter(ConsentRecord.consent_id == consent_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Consent record not found")

    # Vendor data isolation: only the owning vendor (via their linked user
    # account) or a LENDER/ADMIN may toggle a consent record.
    if current_user.role not in ["LENDER", "ADMIN"]:
        vendor = db.query(Vendor).filter(Vendor.vendor_id == c.vendor_id).first()
        if not vendor or vendor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to modify this vendor's consent settings"
            )

    c.granted = granted
    c.revoked_at = datetime.utcnow() if not granted else None

    db.add(AuditLog(
        user_id=current_user.id,
        action="CONSENT_UPDATED",
        resource_type="CONSENT",
        resource_id=consent_id,
        metadata_json={"data_type": c.data_type, "granted": granted}
    ))
    db.commit()
    return {"message": "Consent updated successfully", "granted": c.granted}
