import numpy as np

from typing import List, Dict, Tuple, Any


def _slack_weights(s_max: float, num_bits: int) -> List[float]:
    """
    Binary-encoded weights for a bounded continuous slack variable.

    For an inequality:

        L(x) <= U

    introduce a non-negative slack variable S:

        L(x) + S = U

    The slack variable is represented using binary variables.

    With num_bits bits:

        resolution = s_max / (2^num_bits - 1)

        S = sum(resolution * 2^k * s_k)

    This provides a finite-resolution representation of the slack range
    [0, s_max].
    """
    if s_max <= 1e-9 or num_bits <= 0:
        return []

    resolution = s_max / (2**num_bits - 1)

    return [
        resolution * (2**k)
        for k in range(num_bits)
    ]


def _min_dominant_weight(
    objective_bound: float,
    s_max: float,
    num_bits: int,
    safety_factor: float = 4.0,
) -> float:
    """
    Calculate the minimum penalty weight needed for a constraint to
    dominate the expected-return objective.

    The QUBO minimizes energy, so a constraint violation must introduce
    enough penalty that the optimizer cannot prefer an infeasible
    high-return portfolio simply because it has a better objective value.

    Because slack variables have finite resolution, the smallest
    representable violation is approximately one slack-resolution step.

    Returns 0 when no meaningful slack representation exists.
    """
    if s_max <= 1e-9 or num_bits <= 0:
        return 0.0

    resolution = s_max / (2**num_bits - 1)

    if resolution <= 1e-9:
        return 0.0

    return (
        safety_factor
        * objective_bound
        / (resolution**2)
    )


def _add_inequality_penalty(
    Q: np.ndarray,
    coeffs: Dict[int, float],
    slack_index_weights: List[Tuple[int, float]],
    target: float,
    weight: float,
) -> None:
    """
    Add an inequality penalty to the QUBO matrix.

    Encodes:

        weight * (
            sum(coeff_i * z_i)
            + sum(slack_weight_k * z_k)
            - target
        )^2

    Since binary variables satisfy:

        z_i^2 = z_i

    the resulting expression can be represented as a QUBO matrix.

    Q is maintained symmetrically so that:

        x^T Q x

    evaluates the intended quadratic energy without double-counting
    cross terms.
    """
    terms = (
        list(coeffs.items())
        + list(slack_index_weights)
    )

    c = -target

    # Linear / diagonal terms.
    for idx, coef in terms:
        Q[idx, idx] += weight * (
            coef**2 + 2.0 * c * coef
        )

    # Quadratic cross terms.
    #
    # The expansion contains:
    #
    #   2 * weight * coef_a * coef_b * z_a * z_b
    #
    # Since x^T Q x contains both Q[a,b] and Q[b,a], each symmetric
    # matrix entry receives:
    #
    #   weight * coef_a * coef_b
    #
    # rather than the full 2 * weight * coef_a * coef_b.
    for a in range(len(terms)):
        idx_a, coef_a = terms[a]

        for b in range(a + 1, len(terms)):
            idx_b, coef_b = terms[b]

            cross = weight * coef_a * coef_b

            i, j = (
                (idx_a, idx_b)
                if idx_a < idx_b
                else (idx_b, idx_a)
            )

            Q[i, j] += cross
            Q[j, i] = Q[i, j]


def build_portfolio_qubo(
    vendors_data: List[Dict[str, Any]],
    available_capital: float = 1000000.0,
    max_risk_tolerance: float = 0.25,
    max_category_concentration: float = 0.40,
    lambda_risk: float = 2.5,
    lambda_capital: float = 6.0,
    lambda_concentration: float = 3.0,
    capital_slack_bits: int = 2,
    risk_slack_bits: int = 2,
    concentration_slack_bits: int = 1,
    max_concentration_categories: int = 2,
) -> Tuple[np.ndarray, Dict[str, Any], List[str]]:
    """
    Build a constrained QUBO for lender portfolio allocation.

    Binary vendor variable:

        x_i = 1  -> vendor i selected
        x_i = 0  -> vendor i not selected

    Additional binary variables are used only for inequality slack.

    Optimization objective:

    MAXIMIZE expected portfolio return value

    where:

        expected portfolio return value
            = Σ(expected_return_i * requested_amount_i)

    The objective is scaled by ₹100,000 for numerical stability.
        subject to:

        1. Total requested capital <= available capital

        2. Amount-weighted portfolio risk <= maximum risk tolerance

        3. Category concentration <= configured concentration limit

    Important design decision:

    Risk is NOT included as a soft objective penalty.

    Instead:

        expected return = optimization objective

        risk = hard constraint

    This avoids double-counting risk because the same risk measure is
    already enforced during feasibility validation.

    Since a QUBO minimizes x^T Q x, expected return value is represented
    using negative diagonal coefficients:

        Q[i, i] += -(
            expected_return_i
            * requested_amount_i
            / 100000
        )

    Constraint penalties are then added to the same matrix.

    The final QUBO therefore represents:

        MINIMIZE

            - expected return
            + capital penalty
            + risk constraint penalty
            + concentration constraint penalty

    The returned metadata contains the exact vendor/slack variable layout
    needed by the QAOA solver and classical post-validation.
    """

    # ------------------------------------------------------------------
    # Basic input extraction
    # ------------------------------------------------------------------

    N = len(vendors_data)

    vendor_ids = [
        v["vendor_id"]
        for v in vendors_data
    ]

    returns = np.array(
        [
            float(v.get("expected_return", 0.14))
            for v in vendors_data
        ],
        dtype=float,
    )

    risks = np.array(
        [
            float(v.get("predicted_risk", 0.10))
            for v in vendors_data
        ],
        dtype=float,
    )

    amounts = np.array(
        [
            float(v.get("requested_amount", 25000.0))
            for v in vendors_data
        ],
        dtype=float,
    )

    categories = [
        v.get("business_type", "GENERAL") or "GENERAL"
        for v in vendors_data
    ]

    # ------------------------------------------------------------------
    # Numeric scaling
    # ------------------------------------------------------------------
    #
    # Capital amounts are represented in units of ₹100,000.
    #
    # Example:
    #
    #   ₹25,000 -> 0.25
    #   ₹100,000 -> 1.00
    #
    # This keeps the QUBO numerically manageable.
    # ------------------------------------------------------------------

    scaled_amounts = amounts / 100000.0
    scaled_capital = available_capital / 100000.0

    # ------------------------------------------------------------------
    # Concentration categories
    # ------------------------------------------------------------------
    #
    # To keep the QAOA simulator tractable, only the first configured
    # number of sorted categories receive dedicated QUBO constraints.
    #
    # IMPORTANT:
    # classical_validator.py must still validate every category.
    # ------------------------------------------------------------------

    unique_categories = sorted(set(categories))

    # ------------------------------------------------------------------
    # Hard total-qubit ceiling (performance, not just style)
    # ------------------------------------------------------------------
    #
    # Qiskit Aer's statevector simulation cost grows explosively with
    # qubit count for a densely-connected penalty matrix like this one:
    # empirically, one circuit execution takes ~0.05s at 16 qubits,
    # ~0.2s at 18, ~1s at 20, and ~24s(!) at 24 - and a single QAOA
    # optimization call executes the circuit roughly 10-15 times (a
    # multi-start classical parameter search plus the final sampled
    # run). At 24 qubits that is 3-6 MINUTES per optimization request;
    # at 16-18 it is under a couple of seconds. Since QAOA is already an
    # approximate algorithm whose output is always re-checked by the
    # exact classical validator (with automatic repair on failure - see
    # quantum.py), a coarser slack discretization costs solution
    # precision, not correctness. This cap keeps the DEMO usable
    # regardless of how many vendors/categories happen to be in the
    # pool, rather than silently scaling qubit count (and thus request
    # latency) with pool size.
    MAX_TOTAL_QUBITS = 18
    fixed_slack_bits = capital_slack_bits + risk_slack_bits
    remaining_budget = max(0, MAX_TOTAL_QUBITS - N - fixed_slack_bits)
    effective_max_categories = min(
        max_concentration_categories,
        remaining_budget // max(1, concentration_slack_bits),
    )

    penalized_categories = unique_categories

    excluded_categories = []
    if len(penalized_categories) > max_concentration_categories:
        raise ValueError(
            f"QUBO candidate subproblem has {len(penalized_categories)} categories, "
            f"but max_concentration_categories={max_concentration_categories}. "
            "Select a smaller, category-bounded candidate set."
        )

    # ------------------------------------------------------------------
    # Variable layout
    # ------------------------------------------------------------------
    #
    # Vendor variables:
    #
    #   0 ... N-1
    #
    # Capital slack:
    #
    #   N ...
    #
    # Risk slack:
    #
    #   after capital slack
    #
    # Concentration slack:
    #
    #   after risk slack
    # ------------------------------------------------------------------

    capital_slack_start = N

    risk_slack_start = (
        capital_slack_start
        + capital_slack_bits
    )

    concentration_slack_start = (
        risk_slack_start
        + risk_slack_bits
    )

    concentration_slack_ranges: Dict[str, List[int]] = {}

    cursor = concentration_slack_start

    for category in penalized_categories:
        concentration_slack_ranges[category] = list(
            range(
                cursor,
                cursor + concentration_slack_bits,
            )
        )

        cursor += concentration_slack_bits

    N_total = cursor

    Q = np.zeros(
        (N_total, N_total),
        dtype=float,
    )

    # ------------------------------------------------------------------
    # OBJECTIVE
    # ------------------------------------------------------------------
    #
    # Maximize expected portfolio return VALUE.
    #
    # Each vendor contributes:
    #
    #     expected_return_i * requested_amount_i
    #
    # Because capital is represented in units of ₹100,000, the objective
    # coefficient is scaled as:
    #
    #     expected_return_i * requested_amount_i / 100000
    #
    # QUBO minimizes x^T Q x, therefore:
    #
    #     maximize expected return value
    #
    # becomes:
    #
    #     minimize -expected return value
    #
    # IMPORTANT:
    # Risk is NOT included in the objective.
    # Risk remains a hard constraint below.
    # ------------------------------------------------------------------

    expected_value_coefficients = (
        returns * scaled_amounts
    )

    for i in range(N):
        Q[i, i] += -expected_value_coefficients[i]

    # Upper bound on the total possible objective contribution.
    # This is used for automatic constraint-penalty scaling.
    objective_bound = float(
        np.sum(np.abs(expected_value_coefficients))
    )

    if objective_bound <= 1e-12:
        objective_bound = 1.0

    # ------------------------------------------------------------------
    # CAPITAL CONSTRAINT
    # ------------------------------------------------------------------
    #
    #     sum(amount_i * x_i) <= available_capital
    #
    # Using scaled amounts:
    #
    #     sum(scaled_amount_i * x_i) <= scaled_capital
    #
    # Since all capital coefficients are non-negative:
    #
    #     L_min = 0
    #
    # Maximum required slack:
    #
    #     s_max = scaled_capital
    # ------------------------------------------------------------------

    capital_coeffs = {
        i: float(scaled_amounts[i])
        for i in range(N)
    }

    capital_s_max = max(
        scaled_capital,
        0.0,
    )

    capital_weights = _slack_weights(
        capital_s_max,
        capital_slack_bits,
    )

    capital_slack_idx_weights = [
        (
            capital_slack_start + k,
            weight,
        )
        for k, weight in enumerate(capital_weights)
    ]

    capital_weight = max(
        lambda_capital,
        _min_dominant_weight(
            objective_bound,
            capital_s_max,
            capital_slack_bits,
        ),
    )

    _add_inequality_penalty(
        Q,
        capital_coeffs,
        capital_slack_idx_weights,
        target=scaled_capital,
        weight=capital_weight,
    )

    capital_slack = list(
        range(
            capital_slack_start,
            risk_slack_start,
        )
    )

    # ------------------------------------------------------------------
    # RISK CONSTRAINT
    # ------------------------------------------------------------------
    #
    # Original ratio:
    #
    #   weighted_average_risk <= max_risk_tolerance
    #
    # For a non-empty portfolio:
    #
    #   sum(risk_i * amount_i * x_i)
    #       --------------------------------
    #       sum(amount_i * x_i)
    #
    #       <= tolerance
    #
    # Linearized:
    #
    #   sum(
    #       (risk_i - tolerance)
    #       * amount_i
    #       * x_i
    #   ) <= 0
    #
    # This is the same definition used by classical validation.
    # ------------------------------------------------------------------

    risk_coeffs = {
        i: float(
            (risks[i] - max_risk_tolerance)
            * scaled_amounts[i]
        )
        for i in range(N)
    }

    # The smallest possible value of L(x) occurs when every negative
    # coefficient is selected.
    risk_L_min = sum(
        value
        for value in risk_coeffs.values()
        if value < 0
    )

    # Slack must be capable of compensating for the most negative
    # possible L(x).
    risk_s_max = max(
        -risk_L_min,
        0.0,
    )

    risk_weights = _slack_weights(
        risk_s_max,
        risk_slack_bits,
    )

    risk_slack_idx_weights = [
        (
            risk_slack_start + k,
            weight,
        )
        for k, weight in enumerate(risk_weights)
    ]

    risk_constraint_weight = max(
        lambda_risk,
        _min_dominant_weight(
            objective_bound,
            risk_s_max,
            risk_slack_bits,
        ),
    )

    _add_inequality_penalty(
        Q,
        risk_coeffs,
        risk_slack_idx_weights,
        target=0.0,
        weight=risk_constraint_weight,
    )

    risk_slack = list(
        range(
            risk_slack_start,
            concentration_slack_start,
        )
    )

    # ------------------------------------------------------------------
    # CONCENTRATION CONSTRAINT
    # ------------------------------------------------------------------
    #
    # For every penalized business category:
    #
    #     category_amount
    #         <=
    #     max_category_concentration
    #     * available_capital
    #
    # This matches the current classical validator definition.
    #
    # IMPORTANT:
    # Only the configured number of categories receive QUBO penalties.
    # The classical validator must check ALL categories.
    # ------------------------------------------------------------------

    concentration_details: Dict[str, Any] = {}

    concentration_slack: Dict[str, List[int]] = {}

    concentration_target_scaled = max(
        max_category_concentration
        * scaled_capital,
        0.0,
    )

    for category in penalized_categories:

        conc_coeffs = {
            i: float(scaled_amounts[i])
            for i in range(N)
            if categories[i] == category
        }

        # All concentration coefficients are non-negative,
        # therefore L_min = 0.
        conc_s_max = concentration_target_scaled

        conc_weights = _slack_weights(
            conc_s_max,
            concentration_slack_bits,
        )

        conc_idx_weights = [
            (
                concentration_slack_ranges[category][k],
                weight,
            )
            for k, weight in enumerate(conc_weights)
        ]

        conc_weight = max(
            lambda_concentration,
            _min_dominant_weight(
                objective_bound,
                conc_s_max,
                concentration_slack_bits,
            ),
        )

        _add_inequality_penalty(
            Q,
            conc_coeffs,
            conc_idx_weights,
            target=concentration_target_scaled,
            weight=conc_weight,
        )

        concentration_slack[category] = (
            concentration_slack_ranges[category]
        )

        concentration_details[category] = {
            "slack_qubits": concentration_slack_bits,
            "slack_max_value_scaled": round(
                conc_s_max,
                4,
            ),
            "penalty_weight_floor": (
                lambda_concentration
            ),
            "penalty_weight_effective": round(
                conc_weight,
                4,
            ),
        }

    # ------------------------------------------------------------------
    # ISING REPRESENTATION FOR REPORTING
    # ------------------------------------------------------------------
    #
    # Convert the QUBO matrix into the h-vector used for reporting.
    #
    # This does not change the optimization problem.
    # ------------------------------------------------------------------

    h_vector = np.zeros(
        N_total,
        dtype=float,
    )

    for i in range(N_total):
        h_vector[i] = (
            -0.5 * Q[i, i]
            -0.25
            * sum(
                Q[i, j] + Q[j, i]
                for j in range(N_total)
                if j != i
            )
        )

    # ------------------------------------------------------------------
    # Slack qubit collection
    # ------------------------------------------------------------------

    all_slack_qubits = sorted(
        set(capital_slack)
        | set(risk_slack)
        | {
            index
            for indices in concentration_slack.values()
            for index in indices
        }
    )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    qubo_metadata = {
        # Basic dimensions
        "num_variables": N_total,
        "num_vendor_qubits": N,
        "num_slack_qubits": N_total - N,

        # Slack variables
        "slack_qubit_indices": all_slack_qubits,
        "capital_slack_qubits": capital_slack,
        "risk_slack_qubits": risk_slack,
        "concentration_slack_qubits": concentration_slack,

        # Portfolio constraints
        "available_capital": available_capital,
        "max_risk_tolerance": max_risk_tolerance,
        "max_category_concentration": (
            max_category_concentration
        ),

        # QUBO information
        "qubo_matrix_shape": list(Q.shape),
        "ising_h_vector": [
            round(float(h), 4)
            for h in h_vector
        ],

        # Objective information
       # Objective information
        "objective": "maximize_expected_return_value",
        "objective_type": "expected_portfolio_return_value",
        "objective_unit": "scaled_return_value_per_100k",
        "objective_formula": (
            "sum(expected_return_i * requested_amount_i "
            "/ 100000 * x_i)"
        ),
        "objective_bound": round(
            objective_bound,
            4,
        ),

        # Penalty configuration
        "penalty_weights": {
            "capital_weight_floor": lambda_capital,
            "capital_weight_effective": round(
                capital_weight,
                4,
            ),
            "risk_constraint_weight_floor": lambda_risk,
            "risk_constraint_weight_effective": round(
                risk_constraint_weight,
                4,
            ),
            "concentration_weight_floor": (
                lambda_concentration
            ),
        },

        # Exact mathematical definitions
        "constraint_definitions": {
            "capital": (
                "sum(requested_amount_i * x_i) "
                "<= available_capital"
            ),

            "risk": (
                "sum((predicted_risk_i - "
                "max_risk_tolerance) * "
                "requested_amount_i * x_i) <= 0 "
                "(equivalently: amount-weighted "
                "average risk of selected portfolio "
                "<= max_risk_tolerance)"
            ),

            "concentration": (
                "for each penalized business_type "
                "category: sum(requested_amount_i * "
                "x_i) <= max_category_concentration "
                "* available_capital; "
                "classical_validator checks ALL "
                "categories regardless of this cap"
            ),
        },

        # Constraint metadata
        "constraints": {
            "capital": {
                "inequality": (
                    "sum(amount_i * x_i) "
                    "<= available_capital"
                ),
                "slack_qubits": capital_slack_bits,
                "slack_max_value_scaled": round(
                    capital_s_max,
                    4,
                ),
                "penalty_weight_effective": round(
                    capital_weight,
                    4,
                ),
            },

            "risk": {
                "inequality": (
                    "weighted_avg_portfolio_risk "
                    "<= max_risk_tolerance "
                    "(linearized)"
                ),
                "slack_qubits": risk_slack_bits,
                "slack_max_value_scaled": round(
                    risk_s_max,
                    4,
                ),
                "penalty_weight_effective": round(
                    risk_constraint_weight,
                    4,
                ),
            },

            "concentration": {
                "inequality": (
                    "category capital <= "
                    "max_category_concentration "
                    "* available_capital"
                ),
                "categories_penalized": (
                    penalized_categories
                ),
                "categories_excluded": (
                    excluded_categories
                ),
                "per_category": (
                    concentration_details
                ),
            },
        },

        # Variable layout
        "variable_layout": {
            "vendor_variable_indices": list(
                range(N)
            ),
            "capital_slack_indices": capital_slack,
            "risk_slack_indices": risk_slack,
            "concentration_slack_indices": (
                concentration_slack_ranges
            ),
        },
    }

    return (
        Q,
        qubo_metadata,
        vendor_ids,
    )