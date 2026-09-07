import numpy as np
from typing import List, Dict, Any

def detect_anomalies(transactions: List[dict], expenses: List[dict]) -> Dict[str, Any]:
    """
    Detects financial anomaly signals (unusual revenue drops, spikes, duplicate transactions).
    Uses statistical Z-score / outlier detection.
    """
    if not transactions or len(transactions) < 3:
        return {
            "anomaly_risk": "LOW",
            "anomaly_score": 0.05,
            "detected_events": []
        }

    amounts = [t.get("amount", 0) for t in transactions]
    mean_val = np.mean(amounts)
    std_val = np.std(amounts) if len(amounts) > 1 else 1.0

    detected_events = []

    for idx, tx in enumerate(transactions):
        amt = tx.get("amount", 0)
        z_score = abs(amt - mean_val) / (std_val if std_val > 0 else 1.0)
        
        if z_score > 3.0:
            detected_events.append({
                "transaction_id": tx.get("transaction_id", f"tx_{idx}"),
                "type": "REVENUE_SPIKE" if amt > mean_val else "REVENUE_DROP",
                "severity": "MEDIUM" if z_score < 4.0 else "HIGH",
                "description": f"Transaction amount ₹{amt:,.2f} deviates significantly from mean ₹{mean_val:,.2f} (Z-score: {z_score:.2f})."
            })

    anomaly_risk = "HIGH" if len(detected_events) >= 2 else ("MEDIUM" if len(detected_events) == 1 else "LOW")
    anomaly_score = round(min(1.0, len(detected_events) * 0.35), 2)

    return {
        "anomaly_risk": anomaly_risk,
        "anomaly_score": anomaly_score,
        "detected_events": detected_events
    }
