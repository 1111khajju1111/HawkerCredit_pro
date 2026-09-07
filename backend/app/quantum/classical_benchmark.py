import time
import itertools

import numpy as np

from typing import List, Dict, Any, Optional

from app.quantum.portfolio_metrics import (
    weighted_portfolio_risk,
    weighted_portfolio_return,
    business_objective,
)

# Brute-force enumeration is EXACT (provably optimal) and is used whenever
# the problem is small enough for 2^N to be tractable. Above this size we
# transparently fall back to a greedy heuristic and label it as such -
# never as "MILP" or "exact" when it is not.
MAX_EXACT_N = 20


def _feasible_return(
    selected_idx,
    vendors_data,
    available_capital,
    max_risk_tolerance,
    max_category_concentration,
) -> Optional[float]:
    """
    Return the canonical business objective for a candidate subset if it is
    feasible, otherwise return None.

    The optimization objective is expected portfolio return.

    Feasibility uses the SAME three definitions as
    classical_validator.validate_portfolio_solution and the QUBO constraints:

      1. total capital <= available_capital
      2. amount-weighted average risk <= max_risk_tolerance
      3. per-category capital <=
         max_category_concentration * available_capital

    Risk is a HARD CONSTRAINT, not an additional penalty in the objective.
    This prevents double-counting risk because risk is already enforced by
    the portfolio feasibility constraints.
    """
    if not selected_idx:
        return 0.0

    total_capital = 0.0
    weighted_risk_sum = 0.0
    category_totals: Dict[str, float] = {}

    for i in selected_idx:
        v = vendors_data[i]

        amount = float(v.get("requested_amount", 25000.0))
        risk = float(v.get("predicted_risk", 0.10))

        total_capital += amount
        weighted_risk_sum += risk * amount

        category = v.get("business_type", "GENERAL") or "GENERAL"
        category_totals[category] = (
            category_totals.get(category, 0.0) + amount
        )

    # Constraint 1: capital budget
    if total_capital > available_capital:
        return None

    # Constraint 2: amount-weighted portfolio risk
    avg_risk = (
        weighted_risk_sum / total_capital
        if total_capital > 0
        else 0.0
    )

    if avg_risk > max_risk_tolerance:
        return None

    # Constraint 3: category concentration
    max_allowed_category = (
        max_category_concentration * available_capital
    )

    if any(
        amount > max_allowed_category
        for amount in category_totals.values()
    ):
        return None

    # Canonical optimization objective:
    # maximize expected portfolio return.
    return float(
        business_objective(
            selected_idx,
            vendors_data,
        )
    )


def solve_classical_benchmark(
    Q: np.ndarray,
    vendor_ids: List[str],
    vendors_data: List[Dict[str, Any]],
    available_capital: float = 1000000.0,
    max_risk_tolerance: float = 0.25,
    max_category_concentration: float = 0.40,
) -> Dict[str, Any]:
    """
    Classical baseline solver evaluating the SAME business constraints
    (capital budget, risk tolerance, category concentration) encoded in
    the QUBO/QAOA formulation.

    Optimization objective:
        MAXIMIZE expected portfolio return.

    Risk is treated as a hard feasibility constraint rather than being
    subtracted from expected return. This keeps the classical benchmark,
    QUBO formulation, and reported business objective aligned.

    For N <= MAX_EXACT_N this performs an EXACT brute-force search over
    every feasible subset and returns the provably-optimal allocation.

    For larger N, where 2^N enumeration becomes intractable, it falls
    back to a greedy heuristic and labels it as:

        CLASSICAL_GREEDY_HEURISTIC

    rather than falsely labeling it as MILP or exact.
    """
    start_time = time.time()

    N = len(vendor_ids)

    # ------------------------------------------------------------------
    # EXACT CLASSICAL SEARCH
    # ------------------------------------------------------------------
    if N <= MAX_EXACT_N:
        algorithm_name = "CLASSICAL_EXACT_BRUTE_FORCE"

        # Empty portfolio has objective 0.0.
        # A feasible portfolio must beat it to be selected.
        best_obj = 0.0
        best_selected: List[int] = []

        for r in range(N + 1):
            for combo in itertools.combinations(range(N), r):
                obj = _feasible_return(
                    combo,
                    vendors_data,
                    available_capital,
                    max_risk_tolerance,
                    max_category_concentration,
                )

                if obj is not None and obj > best_obj:
                    best_obj = obj
                    best_selected = list(combo)

        selected_indices = best_selected

    # ------------------------------------------------------------------
    # GREEDY CLASSICAL HEURISTIC
    # ------------------------------------------------------------------
    else:
        algorithm_name = "CLASSICAL_GREEDY_HEURISTIC"

        # Rank candidates primarily by expected return relative to risk.
        # Risk remains a hard constraint during selection.
        sorted_vendors = sorted(
            enumerate(vendors_data),
            key=lambda x: (
                float(x[1].get("expected_return", 0.14))
                / (
                    float(x[1].get("predicted_risk", 0.10))
                    + 1e-5
                )
            ),
            reverse=True,
        )

        selected_indices = []

        current_capital = 0.0
        weighted_risk_sum = 0.0
        category_totals: Dict[str, float] = {}

        max_allowed_category = (
            max_category_concentration * available_capital
        )

        for idx, vendor in sorted_vendors:
            requested_amount = float(
                vendor.get("requested_amount", 25000.0)
            )

            risk = float(
                vendor.get("predicted_risk", 0.10)
            )

            category = (
                vendor.get("business_type", "GENERAL")
                or "GENERAL"
            )

            projected_category_total = (
                category_totals.get(category, 0.0)
                + requested_amount
            )

            projected_capital = (
                current_capital + requested_amount
            )

            projected_weighted_risk = (
                weighted_risk_sum
                + risk * requested_amount
            )

            projected_avg_risk = (
                projected_weighted_risk / projected_capital
                if projected_capital > 0
                else 0.0
            )

            # Same three feasibility checks used by the exact solver
            # and the QUBO formulation.
            if (
                projected_capital <= available_capital
                and projected_avg_risk <= max_risk_tolerance
                and projected_category_total <= max_allowed_category
            ):
                selected_indices.append(idx)

                current_capital = projected_capital
                weighted_risk_sum = projected_weighted_risk
                category_totals[category] = projected_category_total

    # ------------------------------------------------------------------
    # RESULT METRICS
    # ------------------------------------------------------------------
    execution_time = time.time() - start_time

    x_classical = np.zeros(N, dtype=int)

    for i in selected_indices:
        x_classical[i] = 1

    # QUBO vendor-only objective value.
    #
    # The QUBO convention minimizes x^T Q x, while the business objective
    # maximizes expected return. Therefore the diagonal return terms are
    # negative in Q.
    Q_vendor = Q[:N, :N] if Q.shape[0] != N else Q

    classical_obj = (
        float(x_classical.T @ Q_vendor @ x_classical)
        if N > 0
        else 0.0
    )

    selected_vendors = [
        vendor_ids[i]
        for i in selected_indices
    ]

    allocated_capital = float(
        sum(
            vendors_data[i].get(
                "requested_amount",
                25000.0,
            )
            for i in selected_indices
        )
    )

    avg_risk = weighted_portfolio_risk(
        selected_indices,
        vendors_data,
    )

    avg_return = weighted_portfolio_return(
        selected_indices,
        vendors_data,
    )

    # Canonical business objective used for the actual
    # classical-vs-QAOA comparison.
    canonical_business_objective = business_objective(
        selected_indices,
        vendors_data,
    )

    # Qiskit/QAOA bitstrings are represented in reversed qubit order
    # elsewhere in the project, so preserve that convention here.
    classical_bitstring = (
        "".join(str(b) for b in reversed(x_classical))
        if N > 0
        else ""
    )

    return {
        "algorithm": algorithm_name,
        "best_bitstring": classical_bitstring,

        # QUBO energy for technical comparison/debugging.
        "objective_value": round(classical_obj, 4),

        "execution_time_seconds": round(
            execution_time,
            6,
        ),

        "selected_indices": selected_indices,
        "selected_vendors": selected_vendors,

        "allocated_capital": round(
            allocated_capital,
            2,
        ),

        "expected_portfolio_risk": round(
            avg_risk,
            4,
        ),

        "expected_portfolio_return": round(
            avg_return,
            4,
        ),

        # This is the canonical business objective used to compare
        # classical and QAOA solutions.
        "business_objective": round(
            canonical_business_objective,
            6,
        ),

        # Brute force evaluates every possible subset, so for N <= 20
        # the returned feasible solution is provably optimal under the
        # stated constraints and objective.
        "is_provably_optimal": (
            algorithm_name
            == "CLASSICAL_EXACT_BRUTE_FORCE"
        ),

        "feasibility": True,
    }


def compute_solution_metrics(
    qaoa_result: Dict[str, Any],
    classical_result: Dict[str, Any],
    qaoa_feasible: bool,
) -> Dict[str, Any]:
    """
    Compare QAOA and the classical reference using the SAME canonical
    business objective: expected portfolio return.

    Both approaches are evaluated under the same capital, risk, and
    concentration constraints.

    A positive objective gap means the classical reference achieved a
    higher business objective than QAOA.
    """
    classical_obj = float(
        classical_result.get(
            "business_objective",
            0.0,
        )
    )

    qaoa_obj = float(
        qaoa_result.get(
            "business_objective",
            0.0,
        )
    )

    if not qaoa_feasible:
        return {
            "classical_optimal_objective": round(
                classical_obj,
                6,
            ),
            "classical_reference_algorithm": (
                classical_result.get("algorithm")
            ),
            "classical_reference_is_provably_optimal": (
                classical_result.get(
                    "is_provably_optimal",
                    False,
                )
            ),
            "qaoa_objective": None,
            "objective_gap": None,
            "approximation_ratio": None,
            "feasible": False,
        }

    objective_gap = round(
        classical_obj - qaoa_obj,
        6,
    )

    approximation_ratio = None

    if classical_obj > 0:
        approximation_ratio = round(
            qaoa_obj / classical_obj,
            4,
        )

    return {
        "classical_optimal_objective": round(
            classical_obj,
            6,
        ),
        "classical_reference_algorithm": (
            classical_result.get("algorithm")
        ),
        "classical_reference_is_provably_optimal": (
            classical_result.get(
                "is_provably_optimal",
                False,
            )
        ),
        "qaoa_objective": round(
            qaoa_obj,
            6,
        ),
        "objective_gap": objective_gap,
        "approximation_ratio": approximation_ratio,
        "feasible": True,
    }
