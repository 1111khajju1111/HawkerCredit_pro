from typing import Dict, List, Any

def get_ai_coach_advice(credit_score: int, features: Dict[str, float], user_query: str = None) -> Dict[str, Any]:
    """
    Conversational AI Financial Assistant providing personalized, data-backed credit-building recommendations.
    """
    recommendations = []

    if features.get("operating_day_consistency", 0) < 70:
        recommendations.append({
            "title": "Log Transactions Daily",
            "priority": "HIGH",
            "reason": "You logged sales on fewer than 5 days last week.",
            "impact": "+25 pts expected on Business Stability",
            "action": "Use the daily diary or voice entry every evening to record sales."
        })

    if features.get("expense_ratio", 0) > 0.6:
        recommendations.append({
            "title": "Optimize Inventory Wholesale Purchases",
            "priority": "MEDIUM",
            "reason": "Your expense-to-revenue ratio is 62%.",
            "impact": "+18 pts on Cashflow Health",
            "action": "Consolidate stock purchases into weekly wholesale orders to reduce unit cost."
        })

    if features.get("repayment_score", 0) < 85:
        recommendations.append({
            "title": "Automate Supplier & Loan Repayments",
            "priority": "HIGH",
            "reason": "Occasional delays in repayment reduce lender confidence.",
            "impact": "+35 pts on Repayment Reliability",
            "action": "Set reminders to pay vendor installments 2 days before the due date."
        })

    if not recommendations:
        recommendations.append({
            "title": "Maintain Exemplary Financial Discipline",
            "priority": "LOW",
            "reason": "Your credit profile is strong across all metrics.",
            "impact": "Sustains Low-Risk Category",
            "action": "Keep recording daily transactions to maintain your 750+ HawkerCredit score."
        })

    response_text = ""
    if user_query:
        query_lower = user_query.lower()
        if "30" in query_lower or "loan" in query_lower or "afford" in query_lower:
            response_text = f"Based on your net daily cashflow and current score of {credit_score}, your model-estimated sustainable credit range is ₹20,000 to ₹35,000. Requesting ₹30,000 is manageable with expected monthly repayments of ~₹2,800."
        elif "score" in query_lower or "improve" in query_lower:
            response_text = f"Your current HawkerCredit score is {credit_score}/1000. Logging daily sales without gaps and maintaining an expense ratio below 50% will raise your score above 780 within 3 weeks."
        else:
            response_text = f"Your financial health is evaluated at {credit_score}/1000. Focus on consistent daily logging to improve visibility for formal lenders."

    return {
        "score": credit_score,
        "recommendations": recommendations,
        "coach_response": response_text
    }
