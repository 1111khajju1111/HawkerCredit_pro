'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import Link from 'next/link';
import { BarChart2, RefreshCw, CheckCircle2, Cpu, Zap } from 'lucide-react';

export default function BenchmarkPage() {
  useRequireAuth(['LENDER', 'ADMIN']);
  const [capital, setCapital] = useState(1000000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  async function runBenchmark() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getQuantumBenchmark(capital);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'No persisted optimization run is available yet. Run the Quantum Optimizer first.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Reuse the latest persisted optimization. This page must never silently
    // launch a second expensive QAOA simulation on initial render.
    runBenchmark();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border-l-4 border-l-accent flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-accent" /> Quantum vs Classical Benchmark
          </h1>
          <p className="text-xs text-gray-400">Fast replay of the latest persisted QAOA run against its classical exact/greedy baseline. No duplicate quantum simulation is launched here.</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            className="w-40 p-2.5 rounded-xl bg-surfaceLight border border-border text-sm text-white focus:outline-none focus:border-accent"
          />
          <button
            onClick={runBenchmark}
            disabled={loading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-accent to-primary text-white font-bold text-xs flex items-center gap-2"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Cpu className="w-4 h-4" />}
            {loading ? 'Loading saved run...' : 'Refresh Benchmark'}
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-card p-4 text-xs font-bold text-red-400 border border-red-400/40">{error}</div>
      )}

      {!result && !loading && !error && (
        <div className="glass-card p-8 text-center space-y-4">
          <Zap className="w-8 h-8 text-accent mx-auto" />
          <h2 className="text-lg font-bold">No benchmark run yet</h2>
          <p className="text-xs text-gray-400">Run the Quantum Optimizer once. Its QAOA result and classical reference are persisted and will appear here instantly.</p>
          <Link href="/lender/portfolio/optimizer" className="inline-flex px-4 py-2.5 rounded-xl bg-gradient-to-r from-accent to-primary text-white text-xs font-bold">Open Quantum Optimizer</Link>
        </div>
      )}

      {result && (

        <div className="glass-card p-6 space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-surfaceLight/80 text-gray-200 uppercase font-bold border-b border-border">
                <tr>
                  <th className="p-3">Metric</th>
                  <th className="p-3 text-accent">QAOA Quantum ({result.qaoa_quantum.backend})</th>
                  <th className="p-3 text-cyanAccent">Classical Baseline ({result.classical_baseline.algorithm})</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                <tr>
                  <td className="p-3 font-semibold">Selected Vendors</td>
                  <td className="p-3 font-mono text-accent">{result.qaoa_quantum.selected_vendors.join(', ') || '—'}</td>
                  <td className="p-3 font-mono text-cyanAccent">{result.classical_baseline.selected_vendors.join(', ') || '—'}</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Expected Return Objective</td>
                  <td className="p-3 text-accent">{result.qaoa_quantum.business_objective ?? '—'}</td>
                  <td className="p-3 text-cyanAccent">{result.classical_baseline.business_objective ?? '—'}</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Execution Time</td>
                  <td className="p-3 text-accent">{(result.qaoa_quantum.execution_time_seconds * 1000).toFixed(2)} ms</td>
                  <td className="p-3 text-cyanAccent">{(result.classical_baseline.execution_time_seconds * 1000).toFixed(2)} ms</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Allocated Capital</td>
                  <td className="p-3 text-accent">₹{result.qaoa_quantum.allocated_capital.toLocaleString()}</td>
                  <td className="p-3 text-cyanAccent">₹{result.classical_baseline.allocated_capital.toLocaleString()}</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Portfolio Risk</td>
                  <td className="p-3 text-accent">{(result.qaoa_quantum.expected_portfolio_risk * 100).toFixed(1)}%</td>
                  <td className="p-3 text-cyanAccent">{(result.classical_baseline.expected_portfolio_risk * 100).toFixed(1)}%</td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Feasibility</td>
                  <td className="p-3 text-accent">{result.solution_metrics?.feasible ? '✓ PASSED' : '✗ FAILED'}</td>
                  <td className="p-3 text-cyanAccent">✓ PASSED</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="text-[10px] text-gray-500">Technical QUBO energy remains available in run telemetry; this comparison uses the canonical expected-monetary-return objective.</div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-4 rounded-xl bg-surfaceLight/60 border border-border">
              <div className="text-[10px] uppercase text-gray-400 font-bold">Classical Optimum</div>
              <div className="text-lg font-mono text-cyanAccent">{result.solution_metrics?.classical_optimal_objective ?? '—'}</div>
              <div className="text-[10px] text-gray-500">{result.solution_metrics?.classical_reference_algorithm}{result.solution_metrics?.classical_reference_is_provably_optimal ? ' (provably optimal)' : ' (heuristic)'}</div>
            </div>
            <div className="p-4 rounded-xl bg-surfaceLight/60 border border-border">
              <div className="text-[10px] uppercase text-gray-400 font-bold">QAOA Candidate</div>
              <div className="text-lg font-mono text-accent">{result.solution_metrics?.qaoa_objective ?? 'infeasible'}</div>
              <div className="text-[10px] text-gray-500">objective gap: {result.solution_metrics?.objective_gap ?? '—'}</div>
            </div>
            <div className="p-4 rounded-xl bg-surfaceLight/60 border border-border">
              <div className="text-[10px] uppercase text-gray-400 font-bold">Approximation Ratio</div>
              <div className="text-lg font-mono text-accent">{result.solution_metrics?.approximation_ratio != null ? `${(result.solution_metrics.approximation_ratio * 100).toFixed(1)}%` : '—'}</div>
              <div className="text-[10px] text-gray-500">QAOA / classical optimum</div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-surfaceLight/60 border border-border text-xs text-gray-300 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emeraldAccent flex-shrink-0 mt-0.5" />
            <span>
              {result.qaoa_quantum.selected_vendors.slice().sort().join(',') === result.classical_baseline.selected_vendors.slice().sort().join(',')
                ? 'QAOA found the same portfolio as the classical baseline on this run.'
                : 'QAOA is an approximate algorithm and can diverge from the classical baseline, especially at low circuit depth (p) — this is expected, not a bug. The classical post-validator is what ultimately gates any recommendation before a human underwriter sees it.'}
            </span>
          </div>

          {result.disclaimer && (
            <div className="p-3 rounded-xl bg-surfaceLight/40 border border-border/60 text-[11px] text-gray-400 italic">
              {result.disclaimer}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
