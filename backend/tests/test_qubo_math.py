import itertools
import numpy as np
import pytest
from app.quantum.qubo_builder import build_portfolio_qubo

def test_qubo_to_ising_energy_equivalence_exhaustive():
    vendors = [
        {"vendor_id":"v1","business_type":"Tea","predicted_risk":0.10,"expected_return":0.20,"requested_amount":20000},
        {"vendor_id":"v2","business_type":"Veg","predicted_risk":0.20,"expected_return":0.15,"requested_amount":30000},
    ]
    Q, meta, _ = build_portfolio_qubo(vendors, available_capital=100000, max_risk_tolerance=0.25, max_category_concentration=0.5)
    h = np.array(meta["ising_h_vector"], dtype=float)
    const = sum(Q[i,i] / 2 for i in range(len(Q))) + sum(Q[i,j] / 2 for i in range(len(Q)) for j in range(i+1,len(Q)))
    for bits in itertools.product((0,1), repeat=len(Q)):
        x=np.array(bits,dtype=int); z=1-2*x
        energy=float(x @ Q @ x)
        ising=const + float(h @ z)
        for i in range(len(Q)):
            for j in range(i+1,len(Q)):
                ising += ((Q[i,j]+Q[j,i])/4.0) * z[i] * z[j]
        assert energy == pytest.approx(ising)
