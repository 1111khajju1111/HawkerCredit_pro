from typing import Dict, List, Any
import pandas as pd

# Population baselines used only for the human-readable positive/watch
# factor narratives below (thresholds for "is this feature notably good
# or bad"), not for the underlying contribution values when real SHAP is
# available.
BASELINES = {
    "revenue_stability": 55.0,
    "cashflow_score": 50.0,
    "operating_day_consistency": 60.0,
    "repayment_score": 75.0,
    "expense_ratio": 0.50,
    "data_quality_score": 50.0
}

FEATURE_LABELS = {
    "revenue_stability": "Revenue Stability",
    "cashflow_score": "Cashflow Health",
    "operating_day_consistency": "Operating Continuity",
    "repayment_score": "Repayment History",
    "business_stability": "Business Stability",
    "expense_ratio": "Expense Control",
}

MODEL_FEATURES = [
    "revenue_stability", "cashflow_score", "operating_day_consistency",
    "repayment_score", "business_stability", "expense_ratio"
]


def _compute_real_shap_contributions(features: Dict[str, float]):
    """
    Computes GENUINE SHAP (SHapley Additive exPlanations) values using
    `shap.TreeExplainer` against the actual persisted RandomForest model,
    rather than a hand-rolled "SHAP-style" baseline-deviation heuristic.
    Returns None if the model or the `shap` package is unavailable, so
    callers can fall back to an honestly-labeled heuristic instead of
    silently mislabeling the fallback as SHAP.
    """
    try:
        import shap
        from app.ai.scoring_model import get_rf_model

        model_meta = get_rf_model()
        if not model_meta or "model" not in model_meta:
            return None
        rf = model_meta["model"]

        X_df = pd.DataFrame([{k: features.get(k, 0.0) for k in MODEL_FEATURES}])
        explainer = shap.TreeExplainer(rf)
        shap_values = explainer.shap_values(X_df)

        # For a binary RandomForestClassifier, shap_values may come back as
        # a list [class_0_values, class_1_values] or as a single array
        # depending on the shap/sklearn version - normalize to the
        # "repaid" (positive) class contribution.
        if isinstance(shap_values, list):
            row = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        else:
            arr = shap_values
            if arr.ndim == 3:
                row = arr[0, :, 1] if arr.shape[-1] > 1 else arr[0, :, 0]
            else:
                row = arr[0]

        contributions = []
        for feat_name, val in zip(MODEL_FEATURES, row):
            contributions.append({
                "feature": FEATURE_LABELS.get(feat_name, feat_name),
                "raw_feature": feat_name,
                "contribution": round(float(val) * 100.0, 2)  # scaled to score-points for readability
            })
        return contributions
    except Exception:
        return None


def _fallback_heuristic_contributions(features: Dict[str, float]):
    """
    Deterministic baseline-deviation heuristic used ONLY when real SHAP
    values cannot be computed (model or `shap` package unavailable).
    Explicitly NOT labeled as SHAP anywhere in its output.
    """
    contributions = []
    rev_val = features.get("revenue_stability", 50.0)
    contributions.append({"feature": "Revenue Stability", "raw_feature": "revenue_stability",
                           "contribution": round((rev_val - BASELINES["revenue_stability"]) * 0.45, 1)})

    rep_val = features.get("repayment_score", 82.0)
    contributions.append({"feature": "Repayment History", "raw_feature": "repayment_score",
                           "contribution": round((rep_val - BASELINES["repayment_score"]) * 0.50, 1)})

    op_val = features.get("operating_day_consistency", 50.0)
    contributions.append({"feature": "Operating Continuity", "raw_feature": "operating_day_consistency",
                           "contribution": round((op_val - BASELINES["operating_day_consistency"]) * 0.35, 1)})

    exp_val = features.get("expense_ratio", 0.50)
    contributions.append({"feature": "Expense Control", "raw_feature": "expense_ratio",
                           "contribution": round((BASELINES["expense_ratio"] - exp_val) * 60.0, 1)})
    return contributions


def generate_explainability(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes transparent feature-contribution explanations (positive
    drivers vs watch factors). Uses REAL SHAP values (via
    `shap.TreeExplainer` on the persisted RandomForest model) whenever the
    model is available, and only falls back to a clearly-labeled
    deterministic heuristic when it is not - the output always reports
    which method (`explanation_method`) was actually used.
    """
    positive_factors = []
    watch_factors = []

    shap_contributions = _compute_real_shap_contributions(features)
    if shap_contributions is not None:
        feature_contributions = shap_contributions
        explanation_method = "SHAP_TREE_EXPLAINER"
    else:
        feature_contributions = _fallback_heuristic_contributions(features)
        explanation_method = "DETERMINISTIC_BASELINE_HEURISTIC"

    contrib_by_feature = {c["raw_feature"]: c["contribution"] for c in feature_contributions}

    # 1. Revenue Stability
    rev_val = features.get("revenue_stability", 50.0)
    rev_dev = rev_val - BASELINES["revenue_stability"]
    rev_impact = contrib_by_feature.get("revenue_stability", 0.0)
    if rev_dev >= 5.0:
        positive_factors.append({
            "title": "Consistent Daily Turnover",
            "impact": f"+{abs(rev_impact):.0f} pts",
            "detail": f"Revenue stability ({rev_val:.1f}) exceeds population baseline of {BASELINES['revenue_stability']}."
        })
    elif rev_dev < -5.0:
        watch_factors.append({
            "title": "Revenue Volatility",
            "impact": f"-{abs(rev_impact):.0f} pts",
            "detail": "Fluctuations in daily sales increase short-term cashflow uncertainty."
        })

    # 2. Repayment Score
    rep_val = features.get("repayment_score", 82.0)
    rep_dev = rep_val - BASELINES["repayment_score"]
    rep_impact = contrib_by_feature.get("repayment_score", 0.0)
    if rep_dev >= 5.0:
        positive_factors.append({
            "title": "Punctual Repayment History",
            "impact": f"+{abs(rep_impact):.0f} pts",
            "detail": "Consistently settles micro-loans and supplier credit on or before due date."
        })
    elif rep_dev < -5.0:
        watch_factors.append({
            "title": "Repayment Delay Signals",
            "impact": f"-{abs(rep_impact):.0f} pts",
            "detail": "Occasional delays observed in historical loan or supplier payments."
        })

    # 3. Operating Continuity
    op_val = features.get("operating_day_consistency", 50.0)
    op_dev = op_val - BASELINES["operating_day_consistency"]
    op_impact = contrib_by_feature.get("operating_day_consistency", 0.0)
    if op_dev >= 5.0:
        positive_factors.append({
            "title": "High Business Continuity",
            "impact": f"+{abs(op_impact):.0f} pts",
            "detail": f"Operates 6+ days per week reliably ({op_val:.1f}% consistency)."
        })

    # 4. Expense Ratio
    exp_val = features.get("expense_ratio", 0.50)
    exp_impact = contrib_by_feature.get("expense_ratio", 0.0)
    if exp_val <= 0.52:
        positive_factors.append({
            "title": "Healthy Operating Margin",
            "impact": f"+{abs(exp_impact):.0f} pts",
            "detail": f"Expense-to-revenue ratio is well controlled at {exp_val*100:.1f}%."
        })
    else:
        watch_factors.append({
            "title": "High Operating Expense Overhead",
            "impact": f"-{abs(exp_impact):.0f} pts",
            "detail": f"Inventory and stock costs consume {exp_val*100:.1f}% of daily gross turnover."
        })

    # 5. Data Quality Factor
    dq_val = features.get("data_quality_score", 50.0)
    if dq_val < 50.0:
        watch_factors.append({
            "title": "Limited Formal Records / Revoked Consent",
            "impact": "-15 pts",
            "detail": "Data quality rating downgraded due to short history or unconsented categories."
        })

    return {
        "positive_factors": positive_factors,
        "watch_factors": watch_factors,
        "shap_contributions": feature_contributions,
        "explanation_method": explanation_method
    }
