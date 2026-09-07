import time
import numpy as np
from typing import Dict, List, Any, Optional
from app.quantum.portfolio_metrics import weighted_portfolio_risk, weighted_portfolio_return, business_objective


def _energy(bits: np.ndarray, Q: np.ndarray) -> float:
    return float(bits.T @ Q @ bits)


def solve_qaoa(
    Q: np.ndarray,
    vendor_ids: List[str],
    vendors_data: List[Dict[str, Any]],
    p_layers: int = 2,
    shots: int = 1024,
    num_vendor_qubits: Optional[int] = None,
    available_capital: float = 1000000.0,
    max_risk_tolerance: float = 0.25,
    max_category_concentration: float = 0.40,
    optimizer_iterations: int = 12,
) -> Dict[str, Any]:
    """
    Executes the Quantum Approximate Optimization Algorithm (QAOA) on the
    Qiskit Aer quantum simulator.

    Unlike a fixed-angle QAOA ansatz, this runs a genuine CLASSICAL
    OUTER-LOOP optimizer (SciPy COBYLA) that searches over the gamma/beta
    rotation angles to minimize the sampled expectation energy - the
    standard QAOA parameter-optimization loop - rather than using two
    hardcoded angle pairs.

    `Q` may include trailing SLACK qubits (see qubo_builder). Only the
    first `num_vendor_qubits` bits of any measured bitstring represent an
    actual vendor-selection decision; the rest are dropped when decoding.
    """
    start_time = time.time()
    N_total = Q.shape[0]
    N_vendors = num_vendor_qubits if num_vendor_qubits is not None else len(vendor_ids)
    fallback_used = False
    backend_name = "qiskit_aer_qasm_simulator"

    best_bitstring = None
    best_energy = float('inf')
    best_indices: List[int] = []
    circuit_depth = 0
    optimized_gamma = None
    optimized_beta = None

    init_gammas = ([0.45, 0.75] + [0.5] * max(0, p_layers - 2))[:p_layers]
    init_betas = ([0.35, 0.60] + [0.5] * max(0, p_layers - 2))[:p_layers]

    # QAOA acts on an Ising Hamiltonian, not directly on the raw QUBO
    # coefficients. For x in {0,1}^N with x_i=(1-Z_i)/2,
    #
    #   x^T Q x = const + sum_i h_i Z_i + sum_{i<j} J_ij Z_i Z_j
    #
    # where (for a possibly non-symmetric Q)
    #   h_i  = -Q_ii/2 - 1/4 * sum_{j!=i}(Q_ij + Q_ji)
    #   J_ij =  1/4 * (Q_ij + Q_ji)
    #
    # The QUBO builder exposes the same h-vector in its metadata. Compute
    # it here from Q so this solver remains self-contained and cannot drift
    # from the matrix it actually receives. The omitted constant only adds a
    # global phase and therefore does not affect QAOA sampling.
    ising_h = np.zeros(N_total, dtype=float)
    ising_J = np.zeros((N_total, N_total), dtype=float)
    for i in range(N_total):
        ising_h[i] = (
            -0.5 * Q[i, i]
            - 0.25 * sum(
                Q[i, j] + Q[j, i]
                for j in range(N_total)
                if j != i
            )
        )
        for j in range(i + 1, N_total):
            ising_J[i, j] = 0.25 * (Q[i, j] + Q[j, i])

    def build_circuit(gammas: List[float], betas: List[float]):
        from qiskit import QuantumCircuit

        qc = QuantumCircuit(N_total, N_total)
        for q in range(N_total):
            qc.h(q)

        for layer in range(p_layers):
            g = gammas[layer]
            b = betas[layer]

            # exp(-i * gamma * h_i Z_i) -> RZ(2*gamma*h_i)
            for i in range(N_total):
                if abs(ising_h[i]) > 1e-9:
                    qc.rz(2 * g * ising_h[i], i)

            # exp(-i * gamma * J_ij Z_i Z_j) -> RZZ(2*gamma*J_ij)
            for i in range(N_total):
                for j in range(i + 1, N_total):
                    if abs(ising_J[i, j]) > 1e-9:
                        qc.rzz(2 * g * ising_J[i, j], i, j)

            for i in range(N_total):
                qc.rx(2 * b, i)

        qc.measure(range(N_total), range(N_total))
        return qc

    def run_circuit(qc, n_shots: int):
        from qiskit_aer import AerSimulator
        sim = AerSimulator()
        result = sim.run(qc, shots=n_shots).result()
        return result.get_counts()

    def expected_energy(params: np.ndarray) -> float:
        half = len(params) // 2
        gammas, betas = list(params[:half]), list(params[half:])
        try:
            qc = build_circuit(gammas, betas)
            counts = run_circuit(qc, n_shots=256)
        except Exception:
            return float('inf')
        total = sum(counts.values())
        exp_val = 0.0
        for bitstr, count in counts.items():
            x = np.array([int(b) for b in reversed(bitstr)])
            exp_val += _energy(x, Q) * (count / total)
        return exp_val

    try:
        from scipy.optimize import minimize

        # Multi-start COBYLA: QAOA's energy landscape at low circuit depth
        # is highly non-convex, so a single starting point often stalls in
        # a poor local optimum (e.g. the all-zeros bitstring). Trying a
        # handful of different starting angles and keeping the best is the
        # standard mitigation for this and stays entirely classical.
        rng = np.random.default_rng(42)
        candidate_starts = [np.array(init_gammas + init_betas)]
        for _ in range(2):
            candidate_starts.append(rng.uniform(0.1, 1.4, size=2 * p_layers))

        best_params = candidate_starts[0]
        best_val = float('inf')
        for x0 in candidate_starts:
            opt_result = minimize(
                expected_energy,
                x0,
                method="COBYLA",
                options={"maxiter": max(4, optimizer_iterations // len(candidate_starts)), "rhobeg": 0.3},
            )
            if opt_result.fun < best_val:
                best_val = opt_result.fun
                best_params = opt_result.x
        opt_params = best_params
    except Exception:
        opt_params = np.array(init_gammas + init_betas)

    try:
        half = len(opt_params) // 2
        gammas = list(opt_params[:half])
        betas = list(opt_params[half:])
        optimized_gamma = [round(float(g), 4) for g in gammas]
        optimized_beta = [round(float(b), 4) for b in betas]

        qc = build_circuit(gammas, betas)
        circuit_depth = qc.depth()
        counts = run_circuit(qc, n_shots=shots)

        for bitstr, count in counts.items():
            # Qiskit bitstring order is right-to-left (little endian)
            x_candidate = np.array([int(bit) for bit in reversed(bitstr)])
            energy = _energy(x_candidate, Q)

            if energy < best_energy:
                best_energy = energy
                best_bitstring = bitstr
                best_indices = [i for i, val in enumerate(x_candidate[:N_vendors]) if val == 1]

    except Exception:
        # Genuine quantum execution failed (e.g. Qiskit/Aer unavailable).
        # Fall back to the DETERMINISTIC classical solver - never to
        # random guessing - and label the backend honestly so downstream
        # consumers can tell a quantum run apart from a classical one.
        fallback_used = True
        backend_name = "classical_fallback_qiskit_unavailable"
        from app.quantum.classical_benchmark import solve_classical_benchmark

        fb_res = solve_classical_benchmark(
            Q,
            vendor_ids,
            vendors_data,
            available_capital=available_capital,
            max_risk_tolerance=max_risk_tolerance,
            max_category_concentration=max_category_concentration,
        )
        best_indices = fb_res["selected_indices"]
        x_full = np.zeros(N_total, dtype=int)
        for i in best_indices:
            x_full[i] = 1
        best_bitstring = "".join(str(b) for b in reversed(x_full))
        best_energy = _energy(x_full, Q)
        circuit_depth = 0

    execution_time = time.time() - start_time
    selected_vendors = [vendor_ids[i] for i in best_indices]

    total_allocated = sum(vendors_data[i].get("requested_amount", 25000.0) for i in best_indices)
    avg_risk = weighted_portfolio_risk(best_indices, vendors_data)
    avg_return = weighted_portfolio_return(best_indices, vendors_data)
    canonical_business_objective = business_objective(best_indices, vendors_data)

    return {
        "algorithm": "QAOA",
        "backend": backend_name,
        "num_qubits": N_total,
        "num_vendor_qubits": N_vendors,
        "shots": shots,
        "p_layers": p_layers,
        "circuit_depth": circuit_depth,
        "optimized_gamma": optimized_gamma,
        "optimized_beta": optimized_beta,
        "best_bitstring": best_bitstring or ("1" * N_total),
        "objective_value": round(float(best_energy), 4),
        "execution_time_seconds": round(execution_time, 4),
        "selected_indices": best_indices,
        "selected_vendors": selected_vendors,
        "allocated_capital": round(total_allocated, 2),
        "expected_portfolio_risk": round(avg_risk, 4),
        "expected_portfolio_return": round(avg_return, 4),
        "business_objective": round(canonical_business_objective, 6),
        "fallback_used": fallback_used,
        # NOTE: there is deliberately no "solution_quality" score here.
        # QAOA on its own has no ground truth to grade itself against - a
        # single number like "94%" with no defensible calculation behind
        # it is not reported. The real quality signal (approximation ratio
        # / objective gap vs. the classical exact optimum, and pass/fail
        # feasibility) is computed by the caller in quantum.py, which is
        # the only place that has BOTH the QAOA result and the classical
        # benchmark result needed to compute it honestly.
    }
