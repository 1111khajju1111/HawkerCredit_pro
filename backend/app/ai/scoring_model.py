import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'credit_rf_model.joblib')

_loaded_model_meta = None

def get_rf_model():
    global _loaded_model_meta
    if _loaded_model_meta is None:
        if os.path.exists(MODEL_PATH):
            try:
                _loaded_model_meta = joblib.load(MODEL_PATH)
            except Exception:
                _loaded_model_meta = None
    return _loaded_model_meta

def predict_credit_score(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Predicts Repayment Probability P(repay) and HawkerCredit Alternative Score (300-900).
    Uses persisted RandomForest model if available, with deterministic fallback.
    100% deterministic: Identical inputs ALWAYS produce identical output.
    """
    rev_stab = features.get("revenue_stability", 50.0)
    cash_score = features.get("cashflow_score", 50.0)
    op_cons = features.get("operating_day_consistency", 50.0)
    rep_score = features.get("repayment_score", 55.0)
    insufficient_data = bool(features.get("insufficient_data", False))
    data_quality_score = features.get("data_quality_score", 50.0)
    bus_stab = features.get("business_stability", 50.0)
    exp_ratio = features.get("expense_ratio", 0.5)

    model_meta = get_rf_model()

    if model_meta and "model" in model_meta:
        rf = model_meta["model"]
        X_df = pd.DataFrame([{
            "revenue_stability": rev_stab,
            "cashflow_score": cash_score,
            "operating_day_consistency": op_cons,
            "repayment_score": rep_score,
            "business_stability": bus_stab,
            "expense_ratio": exp_ratio
        }])
        if hasattr(rf, "predict_proba"):
            # RandomForestClassifier: read P(repaid=1) directly via
            # predict_proba, the methodologically correct way to obtain a
            # probability estimate from a classification model (rather
            # than treating a regressor's raw numeric output as if it
            # were already a calibrated probability).
            repayment_prob = float(rf.predict_proba(X_df)[0][1])
        else:
            # Backward compatibility with an older persisted regressor.
            repayment_prob = float(rf.predict(X_df)[0])
        model_version = model_meta.get("version", "v2.0.0-RF-Persisted")
    else:
        # Deterministic mathematical fallback
        weighted = (
            (rev_stab * 0.25) +
            (cash_score * 0.25) +
            (op_cons * 0.20) +
            (rep_score * 0.25) +
            (bus_stab * 0.15) -
            (exp_ratio * 30.0)
        ) / 100.0
        repayment_prob = float(np.clip(weighted, 0.40, 0.98))
        model_version = "v2.0.0-Deterministic-Fallback"

    repayment_prob = float(np.clip(repayment_prob, 0.40, 0.98))

    # Never turn missing/insufficient history into a falsely confident score.
    if insufficient_data:
        repayment_prob = min(repayment_prob, 0.55)

    # Convert Repayment Probability P(repay) to documented credit score range (300 - 900)
    # Score 300 at prob 0.40, Score 900 at prob 0.98
    raw_score = 300.0 + ((repayment_prob - 0.40) / 0.58) * 600.0
    final_score = int(min(900, max(300, round(raw_score))))

    # Risk Category mapping
    if final_score >= 800:
        risk_category = "LOW"
    elif final_score >= 700:
        risk_category = "LOW_MODERATE"
    elif final_score >= 580:
        risk_category = "MODERATE"
    elif final_score >= 460:
        risk_category = "HIGH"
    else:
        risk_category = "VERY_HIGH"

    if insufficient_data:
        confidence = 0.20
    else:
        confidence = float(np.clip(data_quality_score / 100.0, 0.30, 0.95))

    # Sustainable loan affordability range (deterministic calculation based on average transaction scale)
    base_avg_rev = features.get("average_transaction", 250.0) * 15 # estimated monthly volume
    min_credit = max(10000.0, round(base_avg_rev * 1.2, -3))
    max_credit = min(75000.0, round(base_avg_rev * (final_score / 360.0), -3))

    return {
        "score": final_score,
        "risk_category": risk_category,
        "repayment_probability": round(repayment_prob, 4),
        "confidence": round(confidence, 2),
        "insufficient_data": insufficient_data,
        "sustainable_credit_min": float(min_credit),
        "sustainable_credit_max": float(max_credit),
        "model_version": model_version
    }
