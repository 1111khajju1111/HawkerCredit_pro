from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.schema import Vendor, CreditScore, CreditFeature
from app.ai.feature_engineering import check_consent
from app.core.rate_limit import limiter
from app.ai.feature_engineering import compute_vendor_features
from app.ai.scoring_model import predict_credit_score
from app.ai.explainability import generate_explainability
from app.ai.data_quality import calculate_data_quality
from app.core.security import verify_vendor_access

router = APIRouter()


@router.get("/{vendor_id}")
@limiter.limit("30/minute")
def get_credit_profile(
    request: Request,
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Do not score transaction-derived credit intelligence when the vendor
    # has not explicitly granted TRANSACTIONS consent.
    if not check_consent(vendor_id, "TRANSACTIONS", db):
        return {
            "vendor_id": vendor_id,
            "name": vendor.name,
            "business_type": vendor.business_type,
            "consent_required": True,
            "score": None,
            "message": "No credit score can be generated: TRANSACTIONS consent has not been granted."
        }

    txs = [t.__dict__ for t in vendor.transactions]
    exs = [e.__dict__ for e in vendor.expenses]
    reps = []
    for l in vendor.loans:
        for r in l.repayments:
            reps.append(r.__dict__)

    # vendor_id + db passed through (consent enforcement) and actual
    # repayment history passed through (previously this endpoint computed
    # features WITHOUT repayments at all, unlike the transaction-triggered
    # refresh path, so on-demand profile views silently ignored repayment
    # behavior that the background refresh path did account for).
    features = compute_vendor_features(txs, exs, reps, vendor_id=vendor_id, db=db)
    score = predict_credit_score(features)
    explain = generate_explainability(features)
    dq = calculate_data_quality(txs, exs, vendor.__dict__)

    return {
        "vendor_id": vendor_id,
        "name": vendor.name,
        "business_type": vendor.business_type,
        "location": vendor.location,
        "operating_since": vendor.operating_since,
        "operating_days": vendor.operating_days,
        "consent_required": False,
        "score": score["score"],
        "risk_category": score["risk_category"],
        "risk_band": score["risk_category"],
        "repayment_probability": score["repayment_probability"],
        "confidence": score.get("confidence"),
        "insufficient_data": score.get("insufficient_data", False),
        "sustainable_credit_min": score["sustainable_credit_min"],
        "sustainable_credit_max": score["sustainable_credit_max"],
        "data_quality_score": dq["data_quality_score"],
        "confidence_level": dq["confidence_level"],
        "positive_factors": explain["positive_factors"],
        "watch_factors": explain["watch_factors"],
        "shap_contributions": explain.get("shap_contributions", []),
        "explanation_method": explain.get("explanation_method", "UNKNOWN"),
        "features": features,
        "recent_transaction_count": len(txs),
        "recent_expense_count": len(exs),
        "model_version": score["model_version"],
        "disclaimer": (
            "Model-estimated alternative financial intelligence based on consented vendor data; "
            "not an official credit bureau score. The underlying model is trained on SYNTHETIC "
            "repayment data for demonstration purposes and has not been validated against real-world "
            "hawker vendor repayment outcomes." + (" This profile is based on insufficient transaction history - treat the score as low-confidence and preliminary." if score.get("insufficient_data") else "")
        )
    }
