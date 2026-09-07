from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.schema import Vendor, QuantumRun, AuditLog
from app.schemas.dto import QuantumPortfolioRequest, QuantumRunResponse
from app.quantum.qubo_builder import build_portfolio_qubo
from app.quantum.qaoa_solver import solve_qaoa
from app.quantum.classical_benchmark import solve_classical_benchmark, compute_solution_metrics
from app.quantum.classical_validator import validate_portfolio_solution
from app.core.security import require_roles
from app.core.rate_limit import limiter
from app.ai.feature_engineering import check_consent

router = APIRouter()


MAX_QAOA_VENDOR_CANDIDATES = 10
MAX_QAOA_CATEGORIES = 2


def _build_vendor_data(vendors, max_exposure_per_vendor: float = 50000.0):
    rows = []
    for v in vendors:
        risk_val = (1.0 - v.credit_score.repayment_probability) if v.credit_score else 0.15
        ret_val = 0.16 if (v.credit_score and v.credit_score.score >= 700) else 0.12
        req_amt = min(max_exposure_per_vendor, v.credit_score.sustainable_credit_max if v.credit_score else 25000.0)
        rows.append({
            "vendor_id": v.vendor_id,
            "name": v.name,
            "business_type": v.business_type or "GENERAL",
            "predicted_risk": risk_val,
            "expected_return": ret_val,
            "requested_amount": req_amt,
        })
    return rows


def _select_qaoa_candidates(db, requested_vendor_ids=None, max_exposure_per_vendor: float = 50000.0):
    """Select a deterministic, consented 10-vendor subproblem from the eligible pool.

    The platform can have 100+ eligible vendors, but the demo QAOA simulator is
    deliberately bounded to 10 vendor decision qubits. The subset is selected
    from the full consented pool by persisted credit intelligence, with the
    two strongest represented business categories retained so the concentration
    constraint is represented for every category that enters the QUBO.
    """
    query = db.query(Vendor)
    if requested_vendor_ids:
        query = query.filter(Vendor.vendor_id.in_(requested_vendor_ids))
    else:
        query = query.order_by(Vendor.created_at.asc())
    eligible = [v for v in query.all() if check_consent(v.vendor_id, "PORTFOLIO_MATCHING", db)]
    if not eligible:
        return []

    data = _build_vendor_data(eligible, max_exposure_per_vendor)
    # Deterministic category ranking, then deterministic vendor ranking.
    category_scores = {}
    for row in data:
        category_scores.setdefault(row["business_type"], []).append(row)
    if requested_vendor_ids:
        chosen_categories = set(category_scores)
        if len(chosen_categories) > MAX_QAOA_CATEGORIES:
            raise HTTPException(
                status_code=422,
                detail=f"Selected vendor IDs span {len(chosen_categories)} categories; the QAOA demo subproblem supports at most {MAX_QAOA_CATEGORIES}."
            )
    else:
        ranked_categories = sorted(
            category_scores.items(),
            key=lambda kv: (
                sum(r["expected_return"] * r["requested_amount"] for r in kv[1]),
                len(kv[1]),
                kv[0],
            ),
            reverse=True,
        )[:MAX_QAOA_CATEGORIES]
        chosen_categories = {name for name, _ in ranked_categories}
    filtered = [r for r in data if r["business_type"] in chosen_categories]
    filtered.sort(
        key=lambda r: (
            r["expected_return"] * r["requested_amount"],
            r["repayment_probability"] if "repayment_probability" in r else -r["predicted_risk"],
            r["vendor_id"],
        ),
        reverse=True,
    )
    if requested_vendor_ids:
        filtered.sort(key=lambda r: (r["expected_return"] * r["requested_amount"], r["vendor_id"]), reverse=True)
        return filtered[:MAX_QAOA_VENDOR_CANDIDATES]

    # Round-robin by category preserves representation when one category has
    # many more vendors than the other.
    buckets = {c: [r for r in filtered if r["business_type"] == c] for c in chosen_categories}
    ordered = []
    for bucket_index in range(MAX_QAOA_VENDOR_CANDIDATES):
        for category in sorted(buckets):
            if buckets[category]:
                ordered.append(buckets[category].pop(0))
                if len(ordered) >= MAX_QAOA_VENDOR_CANDIDATES:
                    break
        if len(ordered) >= MAX_QAOA_VENDOR_CANDIDATES:
            break
    return ordered


def run_quantum_optimization_impl(
    payload: QuantumPortfolioRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    # 1. Select a deterministic, consented QAOA subproblem from the full eligible pool.
    vendors_data = _select_qaoa_candidates(db, payload.vendor_ids, payload.max_exposure_per_vendor)
    vendors = vendors_data
    if not vendors_data:
        raise HTTPException(status_code=400, detail="No consented vendors available for portfolio optimization")

    # 2. Vendor risk/return parameters are already persisted-derived in vendors_data.

    # 3. Formulate QUBO Matrix & Ising Hamiltonian
    Q, qubo_meta, vendor_ids = build_portfolio_qubo(
        vendors_data,
        available_capital=payload.available_capital,
        max_risk_tolerance=payload.max_risk_tolerance,
        max_category_concentration=payload.max_category_concentration,
    )

    # 4. Execute QAOA / Quantum Solver
    qaoa_res = solve_qaoa(
        Q, vendor_ids, vendors_data,
        p_layers=payload.p_layers,
        shots=payload.shots,
        num_vendor_qubits=qubo_meta["num_vendor_qubits"],
        available_capital=payload.available_capital,
        max_risk_tolerance=payload.max_risk_tolerance,
        max_category_concentration=payload.max_category_concentration,
    )

    # 5. Execute Classical Post-Validator (checks the SAME constraints as the QUBO)
    validation = validate_portfolio_solution(
        qaoa_res["selected_indices"],
        vendors_data,
        available_capital=payload.available_capital,
        max_risk_tolerance=payload.max_risk_tolerance,
        max_category_concentration=payload.max_category_concentration,
    )

    # QAOA is approximate: an infeasible measured candidate must never be
    # presented to a lender as the final portfolio. Keep the raw quantum
    # candidate for audit/comparison, but repair the recommendation with the
    # same deterministic classical reference used for benchmarking.
    quantum_solution_repaired = False
    final_selected_indices = list(qaoa_res["selected_indices"])
    final_selected_vendors = list(qaoa_res["selected_vendors"])
    final_allocated_capital = qaoa_res["allocated_capital"]
    final_expected_risk = qaoa_res["expected_portfolio_risk"]
    final_expected_return = qaoa_res["expected_portfolio_return"]

    if not validation["valid"]:
        repair = solve_classical_benchmark(
            Q, vendor_ids, vendors_data,
            available_capital=payload.available_capital,
            max_risk_tolerance=payload.max_risk_tolerance,
            max_category_concentration=payload.max_category_concentration,
        )
        repair_validation = validate_portfolio_solution(
            repair["selected_indices"], vendors_data,
            available_capital=payload.available_capital,
            max_risk_tolerance=payload.max_risk_tolerance,
            max_category_concentration=payload.max_category_concentration,
        )
        if repair_validation["valid"]:
            quantum_solution_repaired = True
            final_selected_indices = list(repair["selected_indices"])
            final_selected_vendors = list(repair["selected_vendors"])
            final_allocated_capital = repair["allocated_capital"]
            final_expected_risk = repair["expected_portfolio_risk"]
            final_expected_return = repair["expected_portfolio_return"]
            validation = repair_validation

    # 5b. Run the SAME classical benchmark used on /benchmark, so every
    # optimization run has a real, defensible "QAOA vs classical exact"
    # comparison on hand - not a fabricated confidence score. This is what
    # makes the run's quality metrics empirically grounded instead of
    # invented (see compute_solution_metrics docstring).
    classical_res = solve_classical_benchmark(
        Q, vendor_ids, vendors_data,
        available_capital=payload.available_capital,
        max_risk_tolerance=payload.max_risk_tolerance,
        max_category_concentration=payload.max_category_concentration,
    )
    solution_metrics = compute_solution_metrics(qaoa_res, classical_res, qaoa_feasible=not quantum_solution_repaired and validation["valid"])

    # 6. Save QuantumRun record to DB
    q_run = QuantumRun(
        owner_user_id=current_user.id,
        problem_size=len(vendors),
        number_of_variables=qubo_meta["num_variables"],
        qubo_parameters=qubo_meta,
        algorithm=qaoa_res["algorithm"],
        backend=qaoa_res["backend"],
        num_qubits=qaoa_res["num_qubits"],
        shots=qaoa_res["shots"],
        objective_value=qaoa_res["objective_value"],
        execution_time=qaoa_res["execution_time_seconds"],
        # Legacy column name, real number now: the approximation ratio
        # (QAOA total return / classical-optimal total return), or 0.0 if
        # the QAOA candidate was infeasible. No more hardcoded 0.94/0.85.
        solution_quality=solution_metrics["approximation_ratio"] or 0.0,
        result={
            "best_bitstring": qaoa_res["best_bitstring"],
            "circuit_depth": qaoa_res["circuit_depth"],
            "optimized_gamma": qaoa_res["optimized_gamma"],
            "optimized_beta": qaoa_res["optimized_beta"],
            "raw_qaoa_selected_vendors": qaoa_res["selected_vendors"],
            "raw_qaoa_allocated_capital": qaoa_res["allocated_capital"],
            "raw_qaoa_expected_portfolio_risk": qaoa_res["expected_portfolio_risk"],
            "raw_qaoa_expected_portfolio_return": qaoa_res["expected_portfolio_return"],
            "raw_qaoa_business_objective": qaoa_res["business_objective"],
            "selected_vendors": final_selected_vendors,
            "allocated_capital": final_allocated_capital,
            "expected_portfolio_risk": final_expected_risk,
            "expected_portfolio_return": final_expected_return,
            "quantum_solution_repaired": quantum_solution_repaired,
            "validation": validation,
            "classical_benchmark": classical_res,
            "solution_metrics": solution_metrics,
            # Per-vendor allocation detail from THIS run, so portfolio.py
            # (and any other consumer) persists the actual optimized
            # numbers instead of separately-hardcoded placeholders.
            "allocations": [
                {
                    "vendor_id": vendors_data[i]["vendor_id"],
                    "requested_amount": vendors_data[i]["requested_amount"],
                    "allocated_amount": vendors_data[i]["requested_amount"],
                    "predicted_risk": vendors_data[i]["predicted_risk"],
                    "expected_return": vendors_data[i]["expected_return"],
                }
                for i in final_selected_indices
            ],
        },
        status="COMPLETED",
        validation_status=validation["status"],
        fallback_used=qaoa_res["fallback_used"]
    )
    db.add(q_run)
    db.commit()
    db.refresh(q_run)

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action="QUANTUM_OPTIMIZATION_EXECUTED",
        resource_type="QUANTUM_RUN",
        resource_id=q_run.run_id,
        metadata_json={
            "bitstring": qaoa_res["best_bitstring"],
            "p_layers": qaoa_res["p_layers"],
            "circuit_depth": qaoa_res["circuit_depth"],
            "objective_value": qaoa_res["objective_value"],
            "validation_status": validation["status"],
        }
    ))
    db.commit()

    return QuantumRunResponse(
        run_id=q_run.run_id,
        problem_size=q_run.problem_size,
        number_of_variables=q_run.number_of_variables,
        num_vendor_qubits=qubo_meta["num_vendor_qubits"],
        algorithm=q_run.algorithm,
        backend=q_run.backend,
        num_qubits=q_run.num_qubits,
        p_layers=qaoa_res["p_layers"],
        circuit_depth=qaoa_res["circuit_depth"],
        optimized_gamma=qaoa_res["optimized_gamma"],
        optimized_beta=qaoa_res["optimized_beta"],
        best_bitstring=qaoa_res["best_bitstring"],
        objective_value=q_run.objective_value,
        business_objective=qaoa_res["business_objective"],
        execution_time=q_run.execution_time,
        solution_quality=q_run.solution_quality,
        classical_optimal_objective=solution_metrics["classical_optimal_objective"],
        objective_gap=solution_metrics["objective_gap"],
        approximation_ratio=solution_metrics["approximation_ratio"],
        classical_reference_algorithm=solution_metrics["classical_reference_algorithm"],
        classical_reference_is_provably_optimal=solution_metrics["classical_reference_is_provably_optimal"],
        selected_vendors=final_selected_vendors,
        allocated_capital=final_allocated_capital,
        expected_portfolio_risk=final_expected_risk,
        expected_portfolio_return=final_expected_return,
        allocations=q_run.result["allocations"],
        status=q_run.status,
        validation_status=q_run.validation_status,
        fallback_used=q_run.fallback_used,
        created_at=q_run.created_at
    )


@router.post("/optimize", response_model=QuantumRunResponse)
@limiter.limit("10/minute")
def run_quantum_optimization(
    request: Request,
    payload: QuantumPortfolioRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    return run_quantum_optimization_impl(payload, db=db, current_user=current_user)

@router.get("/runs/latest")
@limiter.limit("60/minute")
def get_latest_quantum_run(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    q_query = db.query(QuantumRun)
    if current_user.role != "ADMIN":
        q_query = q_query.filter(QuantumRun.owner_user_id == current_user.id)
    q_run = q_query.order_by(QuantumRun.created_at.desc()).first()
    if not q_run:
        raise HTTPException(status_code=404, detail="No quantum optimization run has been persisted yet")
    return q_run


@router.get("/runs/{run_id}")
@limiter.limit("60/minute")
def get_quantum_run(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    q_query = db.query(QuantumRun).filter(QuantumRun.run_id == run_id)
    if current_user.role != "ADMIN":
        q_query = q_query.filter(QuantumRun.owner_user_id == current_user.id)
    q_run = q_query.first()
    if not q_run:
        raise HTTPException(status_code=404, detail="Quantum run not found")
    return q_run


@router.get("/benchmark")
@limiter.limit("20/minute")
def get_quantum_vs_classical_benchmark(
    request: Request,
    available_capital: float = 1000000.0,
    max_risk_tolerance: float = 0.45,
    max_category_concentration: float = 0.40,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["LENDER", "ADMIN"])),
):
    # A completed optimizer run already persisted the exact QAOA result and
    # its classical reference. Reuse it for the benchmark screen instead of
    # executing a second expensive QAOA simulation.
    latest_query = db.query(QuantumRun)
    if current_user.role != "ADMIN":
        latest_query = latest_query.filter(QuantumRun.owner_user_id == current_user.id)
    latest = latest_query.order_by(QuantumRun.created_at.desc()).first()
    if latest and latest.result and all([
        abs(float(latest.qubo_parameters.get("available_capital", available_capital)) - available_capital) < 0.01,
        abs(float(latest.qubo_parameters.get("max_risk_tolerance", max_risk_tolerance)) - max_risk_tolerance) < 1e-9,
        abs(float(latest.qubo_parameters.get("max_category_concentration", max_category_concentration)) - max_category_concentration) < 1e-9,
    ]):
        stored = latest.result
        if stored.get("classical_benchmark") and stored.get("solution_metrics"):
            q = {
                "algorithm": latest.algorithm,
                "backend": latest.backend,
                "best_bitstring": stored.get("best_bitstring", ""),
                "objective_value": latest.objective_value,
                "execution_time_seconds": latest.execution_time,
                "selected_vendors": stored.get("raw_qaoa_selected_vendors", []),
                "allocated_capital": stored.get("raw_qaoa_allocated_capital", 0),
                "expected_portfolio_risk": stored.get("raw_qaoa_expected_portfolio_risk", 0),
                "expected_portfolio_return": stored.get("raw_qaoa_expected_portfolio_return", 0),
                "business_objective": stored.get("raw_qaoa_business_objective"),
            }
            return {
                "run_id": latest.run_id,
                "qaoa_quantum": q,
                "classical_baseline": stored["classical_benchmark"],
                "validation": stored.get("validation", {}),
                "solution_metrics": stored["solution_metrics"],
                "disclaimer": "Replayed from the latest persisted QAOA run; no second quantum simulation was required.",
                "comparison": {
                    "objective_diff": (
                        round(q["business_objective"] - float(stored["classical_benchmark"].get("business_objective", 0)), 6)
                        if q["business_objective"] is not None else None
                    ),
                    "execution_time_diff_ms": round((q["execution_time_seconds"] - float(stored["classical_benchmark"].get("execution_time_seconds", 0))) * 1000, 2),
                    "capital_utilization_diff": round(q["allocated_capital"] - float(stored["classical_benchmark"].get("allocated_capital", 0)), 2),
                },
            }

    vendors_data = _select_qaoa_candidates(db, None, 50000.0)

    if not vendors_data:
        raise HTTPException(status_code=400, detail="No vendors available for benchmark comparison")

    Q, qubo_meta, vendor_ids = build_portfolio_qubo(
        vendors_data,
        available_capital=available_capital,
        max_risk_tolerance=max_risk_tolerance,
        max_category_concentration=max_category_concentration,
    )

    qaoa_res = solve_qaoa(
        Q, vendor_ids, vendors_data, p_layers=2, shots=1024,
        num_vendor_qubits=qubo_meta["num_vendor_qubits"],
        available_capital=available_capital,
        max_risk_tolerance=max_risk_tolerance,
        max_category_concentration=max_category_concentration,
    )
    class_res = solve_classical_benchmark(
        Q, vendor_ids, vendors_data,
        available_capital=available_capital,
        max_risk_tolerance=max_risk_tolerance,
        max_category_concentration=max_category_concentration,
    )
    validation = validate_portfolio_solution(
        qaoa_res["selected_indices"],
        vendors_data,
        available_capital=available_capital,
        max_risk_tolerance=max_risk_tolerance,
        max_category_concentration=max_category_concentration,
    )
    solution_metrics = compute_solution_metrics(qaoa_res, class_res, qaoa_feasible=validation["valid"])

    return {
        "qaoa_quantum": qaoa_res,
        "classical_baseline": class_res,
        "validation": validation,
        "solution_metrics": solution_metrics,
        "disclaimer": (
            "Quantum advantage is not assumed. This experiment measures "
            "solution quality and runtime against a classical baseline "
            "(exact brute force where tractable, otherwise a labeled "
            "greedy heuristic)."
        ),
        "comparison": {
            "objective_diff": round(qaoa_res["business_objective"] - class_res["business_objective"], 6),
            "execution_time_diff_ms": round((qaoa_res["execution_time_seconds"] - class_res["execution_time_seconds"]) * 1000, 2),
            "capital_utilization_diff": round(qaoa_res["allocated_capital"] - class_res["allocated_capital"], 2)
        }
    }
