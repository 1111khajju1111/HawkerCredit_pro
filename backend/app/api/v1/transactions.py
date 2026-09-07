from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Transaction, Vendor, CreditFeature, CreditScore
from app.schemas.dto import TransactionCreate, TransactionResponse
from app.ai.feature_engineering import compute_vendor_features
from app.ai.scoring_model import predict_credit_score
from app.ai.explainability import generate_explainability
from app.core.security import verify_vendor_access

router = APIRouter()


def refresh_vendor_credit(vendor_id: str, db: Session):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        return

    txs = [t.__dict__ for t in vendor.transactions]
    exs = [e.__dict__ for e in vendor.expenses]
    reps = []
    for l in vendor.loans:
        for r in l.repayments:
            reps.append(r.__dict__)

    # vendor_id + db are passed through so feature engineering can enforce
    # per-vendor consent (e.g. a vendor who has revoked TRANSACTIONS
    # consent must not have their transaction history silently used).
    features = compute_vendor_features(txs, exs, reps, vendor_id=vendor_id, db=db)
    score_data = predict_credit_score(features)
    explain = generate_explainability(features)

    # Update or Create CreditFeature
    feat_obj = db.query(CreditFeature).filter(CreditFeature.vendor_id == vendor_id).first()
    if not feat_obj:
        feat_obj = CreditFeature(vendor_id=vendor_id)
        db.add(feat_obj)

    for k, v in features.items():
        if hasattr(feat_obj, k):
            setattr(feat_obj, k, v)

    # Update or Create CreditScore
    score_obj = db.query(CreditScore).filter(CreditScore.vendor_id == vendor_id).first()
    if not score_obj:
        score_obj = CreditScore(vendor_id=vendor_id)
        db.add(score_obj)

    score_obj.score = score_data["score"]
    score_obj.risk_category = score_data["risk_category"]
    score_obj.repayment_probability = score_data["repayment_probability"]
    score_obj.sustainable_credit_min = score_data["sustainable_credit_min"]
    score_obj.sustainable_credit_max = score_data["sustainable_credit_max"]
    score_obj.positive_factors = explain["positive_factors"]
    score_obj.watch_factors = explain["watch_factors"]
    score_obj.model_version = score_data["model_version"]

    db.commit()


@router.post("", response_model=TransactionResponse)
def create_transaction(
    vendor_id: str,
    tx_in: TransactionCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    tx = Transaction(
        vendor_id=vendor_id,
        amount=tx_in.amount,
        transaction_type=tx_in.transaction_type,
        payment_method=tx_in.payment_method,
        source=tx_in.source,
        confidence_score=tx_in.confidence_score
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    refresh_vendor_credit(vendor_id, db)
    return tx


@router.get("/{vendor_id}", response_model=List[TransactionResponse])
def get_vendor_transactions(
    vendor_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_vendor_access),
):
    return db.query(Transaction).filter(Transaction.vendor_id == vendor_id).order_by(Transaction.timestamp.desc()).all()
