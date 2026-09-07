from typing import List, Dict, Any


def validate_portfolio_solution(
    selected_indices: List[int],
    vendors_data: List[Dict[str, Any]],
    available_capital: float,
    max_risk_tolerance: float,
    max_category_concentration: float = 0.40,
) -> Dict[str, Any]:
    """
    Mandatory Classical Post-Validation Stage.
    Verifies that QAOA / Classical portfolio recommendations satisfy the
    SAME hard business rules that are encoded in the QUBO formulation:
      1. Total capital allocated <= available_capital
      2. Amount-weighted average portfolio risk <= max_risk_tolerance
      3. No single business-type category exceeds max_category_concentration
         of available_capital (matches the QUBO's concentration constraint)

    IMPORTANT: "portfolio risk" here is the requested_amount-weighted
    average risk - sum(risk_i * amount_i) / sum(amount_i) - NOT a plain
    unweighted average across selected vendors. This must match
    qubo_builder.build_portfolio_qubo's risk constraint EXACTLY
    (sum((risk_i - tau) * amount_i * x_i) <= 0 is algebraically the same
    inequality), otherwise the QUBO could be optimizing against a
    different definition of "risk" than what this validator enforces -
    which would mean a solution that is genuinely feasible under the
    QUBO's own constraint could still be rejected here (or vice versa).
    """
    if not selected_indices:
        return {
            "valid": False,
            "status": "REJECTED",
            "reason": "No vendors selected in candidate portfolio solution."
        }

    total_capital = sum(vendors_data[i].get("requested_amount", 25000.0) for i in selected_indices)
    weighted_risk_sum = sum(
        vendors_data[i].get("predicted_risk", 0.10) * vendors_data[i].get("requested_amount", 25000.0)
        for i in selected_indices
    )
    avg_risk = (weighted_risk_sum / total_capital) if total_capital > 0 else 0.0

    category_totals: Dict[str, float] = {}
    for i in selected_indices:
        cat = vendors_data[i].get("business_type", "GENERAL") or "GENERAL"
        amt = vendors_data[i].get("requested_amount", 25000.0)
        category_totals[cat] = category_totals.get(cat, 0.0) + amt

    max_allowed_category_capital = max_category_concentration * available_capital

    violations = []

    # Check 1: Capital Budget
    if total_capital > available_capital:
        violations.append(f"Capital budget exceeded: Allocated ₹{total_capital:,.2f} > Available ₹{available_capital:,.2f}")

    # Check 2: Risk Limit
    if avg_risk > max_risk_tolerance:
        violations.append(f"Portfolio risk limit exceeded: Portfolio Risk {avg_risk:.1%} > Risk Tolerance {max_risk_tolerance:.1%}")

    # Check 3: Concentration Limit
    for cat, amt in category_totals.items():
        if amt > max_allowed_category_capital:
            violations.append(
                f"Concentration limit exceeded for category '{cat}': "
                f"₹{amt:,.2f} > {max_category_concentration:.0%} cap of ₹{max_allowed_category_capital:,.2f}"
            )

    if violations:
        return {
            "valid": False,
            "status": "FAILED_FEASIBILITY",
            "violations": violations,
            "allocated_capital": total_capital,
            "portfolio_risk": avg_risk,
            "category_allocation": category_totals
        }

    return {
        "valid": True,
        "status": "PASSED",
        "violations": [],
        "allocated_capital": total_capital,
        "portfolio_risk": avg_risk,
        "category_allocation": category_totals
    }
