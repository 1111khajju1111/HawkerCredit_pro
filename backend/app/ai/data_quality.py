from typing import Dict, Any

def calculate_data_quality(transactions: list, expenses: list, vendor_data: dict) -> Dict[str, Any]:
    """
    Calculates explicit Data Quality Score (0-100) and Confidence Level.
    """
    tx_count = len(transactions)
    ex_count = len(expenses)
    
    # 1. History length score
    history_score = min(30.0, tx_count * 0.5)
    
    # 2. Transaction frequency completeness
    freq_score = min(30.0, (tx_count / 20.0) * 30.0)
    
    # 3. Expense completeness
    expense_score = 20.0 if ex_count >= 5 else (ex_count * 4.0)
    
    # 4. Profile completeness
    profile_score = 20.0 if vendor_data.get("business_type") and vendor_data.get("location") else 10.0
    
    total_dq_score = min(100.0, history_score + freq_score + expense_score + profile_score)
    
    confidence = "HIGH" if total_dq_score >= 80 else ("MEDIUM" if total_dq_score >= 50 else "LOW")
    
    return {
        "data_quality_score": round(total_dq_score, 1),
        "confidence_level": confidence,
        "factors": {
            "transaction_depth": f"{tx_count} records recorded",
            "expense_logging": f"{ex_count} expense entries",
            "profile_completeness": "Complete" if profile_score == 20 else "Partial"
        }
    }
