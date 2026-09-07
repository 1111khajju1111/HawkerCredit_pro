'use client';

import { useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { Sparkles, Cpu, ShieldCheck, CheckCircle2, AlertTriangle, ArrowRight, Play, RefreshCw, BarChart2, Hash, Layers } from 'lucide-react';

export default function QuantumOptimizerPage() {
  useRequireAuth(['LENDER', 'ADMIN']);
  const [capital, setCapital] = useState(1000000);
  const [riskTolerance, setRiskTolerance] = useState(0.25);
  const [pLayers, setPLayers] = useState(2);
  const [shots, setShots] = useState(1024);
  const [running, setRunning] = useState(false);
  const [quantumResult, setQuantumResult] = useState<any>(null);
  const [benchmarkResult, setBenchmarkResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunOptimization = async () => {
    setRunning(true);
    setError(null);
    try {
      // One QAOA execution is enough: the backend persists the classical
      // reference alongside the quantum run. Avoid launching a second QAOA
      // simulation just to populate the comparison table.
      const qRes = await api.runQuantumOptimize(capital, riskTolerance, pLayers, shots);
      setQuantumResult(qRes);
      if (qRes.classical_benchmark && qRes.solution_metrics) {
        setBenchmarkResult({
          run_id: qRes.run_id,
          qaoa_quantum: {
            best_bitstring: qRes.best_bitstring,
            objective_value: qRes.objective_value,
            execution_time_seconds: qRes.execution_time,
            allocated_capital: qRes.allocated_capital,
            expected_portfolio_risk: qRes.expected_portfolio_risk ?? 0,
            selected_vendors: qRes.selected_vendors,
          },
          classical_baseline: qRes.classical_benchmark,
          solution_metrics: qRes.solution_metrics,
          comparison: {
            objective_diff: Number(qRes.business_objective || 0) - Number(qRes.classical_benchmark.business_objective || 0),
            execution_time_diff_ms: (Number(qRes.execution_time) - Number(qRes.classical_benchmark.execution_time_seconds || 0)) * 1000,
            capital_utilization_diff: Number(qRes.allocated_capital) - Number(qRes.classical_benchmark.allocated_capital || 0),
          },
        });
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Optimization failed');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card-quantum p-8 space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/20 border border-accent/40 text-accent text-xs font-bold mb-2">
              <Sparkles className="w-3.5 h-3.5" /> SIGNATURE QUANTUM ENGINE
            </div>
            <h1 className="text-3xl font-extrabold text-white">Quantum Constrained Portfolio Allocation</h1>
            <p className="text-xs text-gray-300">Formulates lender portfolio optimization into QUBO matrix and solves via Qiskit QAOA quantum simulator</p>
          </div>

          <button
            onClick={handleRunOptimization}
            disabled={running}
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-accent via-primary to-cyanAccent text-white font-extrabold text-sm shadow-xl shadow-accent/30 hover:scale-105 transition-transform flex items-center gap-2"
          >
            {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            {running ? 'Executing QAOA Circuit...' : 'Execute QAOA Quantum Optimizer'}
          </button>
        </div>

        {/* Configuration Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-accent/20">
          <div>
            <label className="text-xs font-semibold text-gray-300">Available Capital Budget (₹)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className="w-full mt-1 p-2.5 rounded-xl bg-surfaceLight border border-border text-sm text-white focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-300">Max Risk Tolerance Limit</label>
            <input
              type="number"
              step="0.05"
              value={riskTolerance}
              onChange={(e) => setRiskTolerance(Number(e.target.value))}
              className="w-full mt-1 p-2.5 rounded-xl bg-surfaceLight border border-border text-sm text-white focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-300">QAOA Layers (p)</label>
            <input
              type="number"
              min="1"
              max="4"
              value={pLayers}
              onChange={(e) => setPLayers(Number(e.target.value))}
              className="w-full mt-1 p-2.5 rounded-xl bg-surfaceLight border border-border text-sm text-white focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-300">Quantum Shots</label>
            <input
              type="number"
              value={shots}
              onChange={(e) => setShots(Number(e.target.value))}
              className="w-full mt-1 p-2.5 rounded-xl bg-surfaceLight border border-border text-sm text-white focus:outline-none focus:border-accent"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="glass-card p-4 text-xs font-bold text-red-400 border border-red-400/40">{error}</div>
      )}

      {/* Results Display */}
      {quantumResult && (
        <div className="space-y-6">
          {/* Quantum Circuit Execution Metadata */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-card p-5 space-y-1">
              <div className="text-xs font-semibold text-gray-400">QUBO Problem Size & Qubits</div>
              <div className="text-2xl font-extrabold text-accent">{quantumResult.num_qubits} Qubits</div>
              <p className="text-[11px] text-gray-400">Binary variables x_i in &#123;0, 1&#125;</p>
            </div>
            <div className="glass-card p-5 space-y-1">
              <div className="text-xs font-semibold text-gray-400">QAOA Circuit Depth & Layers</div>
              <div className="text-2xl font-extrabold text-cyanAccent">Depth {quantumResult.circuit_depth} (p={quantumResult.p_layers})</div>
              <p className="text-[11px] text-gray-400">Qiskit Aer QasmSimulator</p>
            </div>
            <div className="glass-card p-5 space-y-1">
              <div className="text-xs font-semibold text-gray-400">Expectation Energy & Bitstring</div>
              <div className="text-xl font-mono font-extrabold text-white truncate">{quantumResult.best_bitstring}</div>
              <p className="text-[11px] text-gray-400">Expected return objective: {quantumResult.business_objective ?? '—'} · QUBO E(x): {quantumResult.objective_value}</p>
            </div>
            <div className="glass-card p-5 space-y-1">
              <div className="text-xs font-semibold text-gray-400">Post-Classical Validation</div>
              <div className="text-2xl font-extrabold text-emeraldAccent flex items-center gap-1.5">
                <CheckCircle2 className="w-5 h-5" /> {quantumResult.validation_status}
              </div>
              <p className="text-[11px] text-gray-400">Passed capital & risk limits</p>
            </div>
          </div>

          <div className="glass-card p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div><div className="text-xs font-bold text-cyanAccent">PERSISTED AUDIT TRACE</div><div className="text-sm text-gray-300">Inspect the exact telemetry recorded for this optimization run.</div></div>
            <Link href={`/lender/decision-trace?run_id=${encodeURIComponent(quantumResult.run_id)}`} className="px-4 py-2 rounded-xl bg-surfaceLight text-white text-xs font-bold border border-border">Open Decision Trace</Link>
          </div>

          <div className="glass-card p-6 space-y-4 border-l-4 border-l-accent">
            <div><h2 className="text-lg font-bold flex items-center gap-2"><Sparkles className="w-5 h-5 text-accent" /> Recommended Vendor Portfolio</h2><p className="text-xs text-gray-400">These are the vendors selected by the validated optimization result. The recommendation is decision support, not an automatic lending approval.</p></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {(quantumResult.selected_vendors || []).map((id:string, i:number) => <div key={id} className="p-4 rounded-xl bg-surfaceLight/60 border border-border"><div className="text-[10px] uppercase text-gray-500">Rank #{i+1}</div><div className="font-mono text-xs text-white mt-1 break-all">{id}</div></div>)}
              {!quantumResult.selected_vendors?.length && <div className="text-xs text-gray-400">No vendor selected under the current constraints.</div>}
            </div>
          </div>

          {/* Side-by-side Quantum vs Classical Benchmark Comparison Table */}
          {benchmarkResult && (
            <div className="glass-card p-6 space-y-4">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-primary" /> Measured Quantum vs Classical Benchmark
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-gray-300">
                  <thead className="bg-surfaceLight/80 text-gray-200 uppercase font-bold border-b border-border">
                    <tr>
                      <th className="p-3">Optimization Metric</th>
                      <th className="p-3 text-accent">Qiskit QAOA Quantum Solver</th>
                      <th className="p-3 text-cyanAccent">Classical Exact / Greedy Baseline</th>
                      <th className="p-3">Empirical Comparison</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    <tr>
                      <td className="p-3 font-semibold">Optimal Bitstring Solution</td>
                      <td className="p-3 font-mono font-bold text-accent">{benchmarkResult.qaoa_quantum.best_bitstring}</td>
                      <td className="p-3 font-mono font-bold text-cyanAccent">{benchmarkResult.classical_baseline.best_bitstring}</td>
                      <td className="p-3 font-semibold text-emeraldAccent">{benchmarkResult.qaoa_quantum.best_bitstring === benchmarkResult.classical_baseline.best_bitstring ? 'Exact Match' : 'Differs (QAOA is approximate)'}</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-semibold">Expected Return Objective</td>
                      <td className="p-3 font-bold text-accent">{benchmarkResult.qaoa_quantum.business_objective ?? '—'}</td>
                      <td className="p-3 font-bold text-cyanAccent">{benchmarkResult.classical_baseline.business_objective ?? '—'}</td>
                      <td className="p-3">{benchmarkResult.comparison.objective_diff}</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-semibold">Execution Runtime</td>
                      <td className="p-3 text-accent">{(benchmarkResult.qaoa_quantum.execution_time_seconds * 1000).toFixed(1)} ms</td>
                      <td className="p-3 text-cyanAccent">{(benchmarkResult.classical_baseline.execution_time_seconds * 1000).toFixed(1)} ms</td>
                      <td className="p-3">{benchmarkResult.comparison.execution_time_diff_ms} ms</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-semibold">Allocated Capital</td>
                      <td className="p-3 text-accent">₹{benchmarkResult.qaoa_quantum.allocated_capital.toLocaleString()}</td>
                      <td className="p-3 text-cyanAccent">₹{benchmarkResult.classical_baseline.allocated_capital.toLocaleString()}</td>
                      <td className="p-3">₹{benchmarkResult.comparison.capital_utilization_diff.toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td className="p-3 font-semibold">Portfolio Risk Level</td>
                      <td className="p-3 text-accent">{(benchmarkResult.qaoa_quantum.expected_portfolio_risk * 100).toFixed(1)}%</td>
                      <td className="p-3 text-cyanAccent">{(benchmarkResult.classical_baseline.expected_portfolio_risk * 100).toFixed(1)}%</td>
                      <td className="p-3 font-semibold text-emeraldAccent">Within Risk Ceiling</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
