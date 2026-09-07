'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ShieldCheck, ArrowRight, Sparkles } from 'lucide-react';

import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';

function DecisionTraceContent() {
  useRequireAuth(['LENDER', 'ADMIN']);

  const searchParams = useSearchParams();

  const runId = searchParams.get('run_id');
  const [selectedStage, setSelectedStage] = useState(1);
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    api
      .getQuantumRun(runId)
      .then(setRun)
      .catch((err) =>
        setError(err.message || 'Unable to load quantum run')
      );
  }, [runId]);

  const result = run?.result || {};
  const validation = result.validation || {};
  const metrics = result.solution_metrics || {};

  const stages = [
    {
      num: 1,
      title: '1. Raw Vendor Activity',
      detail: `${run?.problem_size ?? 'N/A'} consented vendors entered the optimization candidate pool.`,
    },
    {
      num: 2,
      title: '2. Financial Intelligence Inputs',
      detail:
        'Candidate pool transformed into risk, expected-return and requested-exposure parameters.',
    },
    {
      num: 3,
      title: '3. ML Credit Intelligence',
      detail:
        'Vendor credit intelligence is generated from the consented feature pipeline; the optimization run stores only the resulting risk/return inputs.',
    },
    {
      num: 4,
      title: '4. Explainable AI',
      detail:
        'The credit profile exposes feature-level explanations and data-quality/confidence signals before portfolio optimization.',
    },
    {
      num: 5,
      title: '5. QUBO Formulation',
      detail: `${run?.number_of_variables ?? 'N/A'} total binary variables across ${
        run?.num_qubits ?? 'N/A'
      } qubits, including vendor and constraint slack variables.`,
    },
    {
      num: 6,
      title: '6. QAOA Quantum Circuit',
      detail: `${run?.backend ?? 'N/A'} | p=${
        result?.p_layers ?? run?.p_layers ?? 'N/A'
      } | shots=${run?.shots ?? 'N/A'} | energy E(x)=${
        run?.objective_value ?? 'N/A'
      } | bitstring=${result?.best_bitstring ?? 'N/A'}`,
    },
    {
      num: 7,
      title: '7. Classical Validation & Repair',
      detail: `Status: ${
        run?.validation_status ?? 'N/A'
      } | Capital: ₹${Number(
        validation.allocated_capital ?? result.allocated_capital ?? 0
      ).toLocaleString()} | Risk: ${
        validation.portfolio_risk != null
          ? (validation.portfolio_risk * 100).toFixed(2) + '%'
          : 'N/A'
      }${
        result.quantum_solution_repaired
          ? ' | QAOA candidate repaired by classical reference'
          : ''
      }`,
    },
    {
      num: 8,
      title: '8. Human Underwriting Audit',
      detail:
        'The optimization produces decision support only. Final lending approval/rejection remains a human lender action recorded separately in the audit trail.',
    },
  ];

  if (!runId) {
    return (
      <div className="glass-card p-8 space-y-3">
        <h1 className="text-xl font-bold">Decision Trace</h1>
        <p className="text-sm text-gray-400">
          Run a quantum optimization first, then open Decision Trace from that
          run to inspect its persisted telemetry.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border-l-4 border-l-cyanAccent">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-cyanAccent" />
          Full End-to-End Decision Trace Auditability
        </h1>

        <p className="text-xs text-gray-400">
          Persisted telemetry for quantum run{' '}
          <span className="font-mono">{runId}</span>
        </p>
      </div>

      {error && (
        <div className="glass-card p-4 text-xs font-bold text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-2">
          {stages.map((stage) => (
            <button
              key={stage.num}
              onClick={() => setSelectedStage(stage.num)}
              className={`w-full text-left p-4 rounded-xl border text-xs font-semibold flex items-center justify-between transition-colors ${
                selectedStage === stage.num
                  ? 'bg-accent/20 border-accent text-white font-bold'
                  : 'bg-surfaceLight/50 border-border text-gray-300 hover:bg-surfaceLight'
              }`}
            >
              <span>{stage.title}</span>
              <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
            </button>
          ))}
        </div>

        <div className="glass-card p-6 md:col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <span className="text-xs font-bold text-accent">
              STAGE {selectedStage} AUDIT DETAIL
            </span>

            <span className="text-xs font-bold text-emeraldAccent bg-emeraldAccent/10 px-2 py-0.5 rounded-full">
              PERSISTED RUN
            </span>
          </div>

          <h2 className="text-lg font-bold text-white">
            {stages[selectedStage - 1].title}
          </h2>

          <div className="p-4 rounded-xl bg-surfaceLight/80 border border-border font-mono text-xs text-cyanAccent leading-relaxed">
            {stages[selectedStage - 1].detail}
          </div>

          <div className="p-3.5 rounded-xl bg-surfaceLight/40 border border-border text-xs text-gray-400 space-y-1">
            <div>
              Run ID: <strong>{run?.run_id ?? runId}</strong>
            </div>

            <div>
              Created:{' '}
              <strong>
                {run?.created_at
                  ? new Date(run.created_at).toISOString()
                  : 'N/A'}
              </strong>
            </div>

            <div>
              Classical reference:{' '}
              <strong>
                {metrics.classical_reference_algorithm ?? 'N/A'}
              </strong>
            </div>

            <div>
              Approximation ratio:{' '}
              <strong>{metrics.approximation_ratio ?? 'N/A'}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DecisionTracePage() {
  return (
    <Suspense
      fallback={
        <div className="glass-card p-8 flex items-center justify-center">
          <p className="text-sm text-gray-400">
            Loading decision trace...
          </p>
        </div>
      }
    >
      <DecisionTraceContent />
    </Suspense>
  );
}
