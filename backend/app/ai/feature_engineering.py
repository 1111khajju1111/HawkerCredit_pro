import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

def check_consent(vendor_id: str, data_type: str, db=None) -> bool:
    """
    Consent Enforcement Gate. FAILS CLOSED: consent is only ever True when
    a consent record was actually found and its `granted` flag is True.
    Any situation where consent CANNOT be positively confirmed - no
    record exists yet, or the database lookup itself errors out - denies
    processing rather than assuming permission. An earlier version of
    this function returned True on a DB exception (and on a missing
    record), which meant a database hiccup could silently look
    indistinguishable from "the vendor said yes."

    The one exception is when no database is engaged for this call at
    all (`db is None`) - e.g. isolated unit tests computing features from
    raw synthetic data with no consent system in play. There is nothing
    to fail against in that case, so it defaults to permissive.
    """
    if db is None or not vendor_id:
        return True
    try:
        from app.models.schema import ConsentRecord
        consent = db.query(ConsentRecord).filter(
            ConsentRecord.vendor_id == vendor_id,
            ConsentRecord.data_type == data_type
        ).first()
        if consent is not None:
            return bool(consent.granted)
        # No consent record exists for this vendor/data_type: consent was
        # never affirmatively granted, so deny rather than assume.
        return False
    except Exception:
        # Consent cannot be verified due to a database error - fail closed.
        return False

def compute_vendor_features(
    transactions: List[dict],
    expenses: List[dict],
    repayments: List[dict] = None,
    vendor_id: str = None,
    db = None
) -> Dict[str, float]:
    """
    Computes 100% deterministic alternative credit features from raw database activity.
    Enforces active consent gates for data types 'TRANSACTIONS' and 'EXPENSES'.
    NO random variables used in production.
    """
    # 1. Enforce Consent Gates
    has_tx_consent = check_consent(vendor_id, "TRANSACTIONS", db) if vendor_id else True
    has_ex_consent = check_consent(vendor_id, "EXPENSES", db) if vendor_id else True

    effective_txs = transactions if has_tx_consent else []
    effective_exs = expenses if has_ex_consent else []

    if not effective_txs:
        # Insufficient/unconsented data: return a NEUTRAL baseline, not a
        # comfortable-looking one. An earlier version of this baseline
        # used values like repayment_score=70.0 (out of 100) for a vendor
        # with literally zero transaction history - silently fabricating
        # a moderately-good financial profile for someone the system has
        # no actual information about. Every value below sits at or below
        # the middle of its range, and `insufficient_data: True` is always
        # present so callers (the scoring model, the API response, the
        # UI) can surface this honestly instead of treating it as a
        # normal computed score.
        return {
            "revenue_stability": 20.0,
            "revenue_trend": 0.0,
            "transaction_frequency": 0.0,
            "average_transaction": 0.0,
            "expense_ratio": 0.5,
            "cashflow_score": 30.0,
            "operating_day_consistency": 30.0,
            "repayment_score": 50.0,
            "business_stability": 30.0,
            "seasonal_volatility": 15.0,
            "anomaly_score": 0.0,
            "data_quality_score": 10.0 if not has_tx_consent else 20.0,
            "insufficient_data": True
        }

    df_tx = pd.DataFrame(effective_txs)
    df_ex = pd.DataFrame(effective_exs) if effective_exs else pd.DataFrame(columns=['amount', 'timestamp'])

    # Amounts calculation
    tx_amounts = df_tx['amount'].values if 'amount' in df_tx else np.array([0.0])
    avg_tx = float(np.mean(tx_amounts))
    std_tx = float(np.std(tx_amounts)) if len(tx_amounts) > 1 else avg_tx * 0.25

    # 1. Revenue Stability (Lower coefficient of variation = Higher stability)
    cov = (std_tx / avg_tx) if avg_tx > 0 else 1.0
    revenue_stability = min(100.0, max(10.0, 100.0 - (cov * 45.0)))

    # 2. Revenue Trend (Linear regression slope over time)
    if len(tx_amounts) >= 3:
        x_indices = np.arange(len(tx_amounts))
        slope, _ = np.polyfit(x_indices, tx_amounts, 1)
        revenue_trend = float(np.clip(slope / (avg_tx + 1e-5), -0.5, 0.5))
    else:
        revenue_trend = 0.05

    # 3. Total revenue & Expense ratio
    total_rev = float(np.sum(tx_amounts))
    total_exp = float(np.sum(df_ex['amount'].values)) if not df_ex.empty and 'amount' in df_ex else (total_rev * 0.45)

    expense_ratio = min(1.0, max(0.0, total_exp / total_rev)) if total_rev > 0 else 0.5
    net_cash_margin = (total_rev - total_exp) / total_rev if total_rev > 0 else 0.0
    cashflow_score = min(100.0, max(10.0, (net_cash_margin * 75.0) + 25.0))

    # 4. Transaction Frequency & Operating Day Consistency
    tx_count = len(df_tx)
    tx_freq = float(tx_count / 30.0) # daily average over month
    operating_day_consistency = min(100.0, max(20.0, (tx_freq / 1.5) * 100.0))

    # 5. Repayment Score (Deterministic calculation from actual days delayed)
    if repayments and len(repayments) > 0:
        delayed_days = [r.get('days_delayed', 0) for r in repayments]
        avg_delay = float(np.mean(delayed_days))
        repayment_score = min(100.0, max(0.0, 100.0 - (avg_delay * 6.0)))
    else:
        # No prior formal loan history exists to evaluate - this is a
        # genuinely UNKNOWN quantity, not a demonstrated good repayer.
        # An earlier version defaulted this to 82.0 (labeled "neutral")
        # for every first-time borrower, which is a materially
        # optimistic assumption dressed up as neutrality. 55.0 sits at
        # the actual midpoint of the 0-100 range with no data-driven
        # basis to lean positive.
        repayment_score = 55.0

    # 6. Seasonal Volatility (Standard deviation ratio over weekly windows)
    if len(tx_amounts) >= 7:
        weekly_sums = [float(np.sum(tx_amounts[i:i+7])) for i in range(0, len(tx_amounts), 7)]
        std_weekly = float(np.std(weekly_sums)) if len(weekly_sums) > 1 else 0.0
        mean_weekly = float(np.mean(weekly_sums)) if weekly_sums else 1.0
        seasonal_volatility = min(50.0, max(5.0, (std_weekly / (mean_weekly + 1e-5)) * 100.0))
    else:
        seasonal_volatility = 12.5

    # 7. Anomaly Score (Fraction of transactions exceeding 2.5 Z-scores)
    if len(tx_amounts) >= 5 and std_tx > 0:
        z_scores = np.abs((tx_amounts - avg_tx) / std_tx)
        outlier_count = int(np.sum(z_scores > 2.5))
        anomaly_score = round(float((outlier_count / len(tx_amounts)) * 100.0), 2)
    else:
        anomaly_score = 2.0

    # 8. Business Stability Composite
    business_stability = (revenue_stability * 0.35) + (operating_day_consistency * 0.35) + (cashflow_score * 0.30)

    # 9. Data Quality Score (Deterministic calculation)
    # Deducts score if consent for transactions or expenses is revoked!
    base_dq = min(100.0, max(10.0, (tx_count * 1.2) + (20.0 if not df_ex.empty else 0.0) + 25.0))
    if not has_tx_consent:
        base_dq -= 40.0
    if not has_ex_consent:
        base_dq -= 20.0
    data_quality_score = min(100.0, max(5.0, base_dq))

    return {
        "revenue_stability": round(float(revenue_stability), 2),
        "revenue_trend": round(float(revenue_trend), 4),
        "transaction_frequency": round(float(tx_freq), 2),
        "average_transaction": round(float(avg_tx), 2),
        "expense_ratio": round(float(expense_ratio), 4),
        "cashflow_score": round(float(cashflow_score), 2),
        "operating_day_consistency": round(float(operating_day_consistency), 2),
        "repayment_score": round(float(repayment_score), 2),
        "business_stability": round(float(business_stability), 2),
        "seasonal_volatility": round(float(seasonal_volatility), 2),
        "anomaly_score": round(float(anomaly_score), 2),
        "data_quality_score": round(float(data_quality_score), 2),
        "insufficient_data": bool(tx_count < 3)
    }
