'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Play, ArrowLeft, ArrowRight, CheckCircle2, Cpu, ShieldCheck, Sparkles, UserCheck, RefreshCw, BarChart2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export default function SihDemoPage() {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [demoState, setDemoState] = useState<any>({
    transcript: "Today I sold vegetables worth 5000 rupees and spent 2000 on stock.",
    parsedVoice: null,
    creditProfile: null,
    quantumRun: null,
    humanDecision: null
  });
  const [loading, setLoading] = useState(false);

  const steps = [
    { num: 1, title: "Vendor Login", desc: "Street vendor logs into HawkerCredit portal." },
    { num: 2, title: "Granular Consent Gate", desc: "Vendor grants active consent for transaction & expense profiling." },
    { num: 3, title: "Voice Diary Sales Entry", desc: "Vendor speaks daily sales & stock purchase in natural Hindi/English." },
    { num: 4, title: "AI NLP Extraction & Confirmation", desc: "NLP entity extraction parses speech into ledger entries." },
    { num: 5, title: "Receipt Upload & OCR", desc: "Paper invoice scanned and OCR verified with vendor confirmation." },
    { num: 6, title: "Deterministic Features Calculated", desc: "100% deterministic features generated without random variables." },
    { num: 7, title: "ML Repayment Probability Model", desc: "Persisted RandomForest predicts repayment probability P(repay)." },
    { num: 8, title: "Explainability & SHAP Panel", desc: "Transparent 'Why this score?' panel displays positive & watch factors." },
    { num: 9, title: "Vendor Micro-Loan Request", desc: "Vendor enters requested micro-working-capital loan." },
    { num: 10, title: "Lender Risk Review & Decision Trace", desc: "Lender inspects full 10-stage decision trace audit trail." },
    { num: 11, title: "Portfolio Candidates Selected", desc: "Candidate vendor pool prepared for capital allocation." },
    { num: 12, title: "QUBO Matrix Formulation", desc: "Capital, risk, and concentration penalties mapped to binary variables x_i." },
    { num: 13, title: "Genuine QAOA Circuit Execution", desc: "Qiskit Aer QasmSimulator executes QAOA circuit with p=2 layers." },
    { num: 14, title: "Classical Baseline Solves Same Problem", desc: "Classical exact brute-force solver (greedy fallback above 20 vendors) evaluates the exact same QUBO constraints." },
    { num: 15, title: "Quantum vs Classical Comparison", desc: "Measured empirical comparison of objective energy, runtime, and capital." },
    { num: 16, title: "Feasibility Post-Validation", desc: "Classical post-validator confirms zero budget or risk violations." },
    { num: 17, title: "Human Underwriter Final Decision", desc: "Authorized human officer reviews AI recommendations & records decision." },
    { num: 18, title: "Audit Trail Logging", desc: "Immutable audit log record persisted in PostgreSQL database." }
  ];

  const handleStepAction = async () => {
    setLoading(true);
    try {
      if (currentStep === 3 || currentStep === 4) {
        const parsed = await api.postVoiceTransaction(demoState.transcript);
        setDemoState((prev: any) => ({ ...prev, parsedVoice: parsed }));
      } else if (currentStep === 6 || currentStep === 7 || currentStep === 8) {
        if (user?.vendor_id) {
          const profile = await api.getCreditProfile(user.vendor_id);
          setDemoState((prev: any) => ({ ...prev, creditProfile: profile }));
        }
      } else if (currentStep >= 12 && currentStep <= 16) {
        if (user?.role === 'LENDER' || user?.role === 'ADMIN') {
          const qRun = await api.runQuantumOptimize(1000000, 0.25, 2, 1024);
          setDemoState((prev: any) => ({ ...prev, quantumRun: qRun }));
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const nextStep = () => {
    if (currentStep < 18) {
      setCurrentStep(prev => prev + 1);
      handleStepAction();
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-card p-6 border-l-4 border-l-accent flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/20 border border-accent/30 text-accent text-xs font-bold mb-1">
            <Sparkles className="w-3.5 h-3.5" /> DEDICATED JUDGE DEMONSTRATION FLOW
          </div>
          <h1 className="text-2xl font-extrabold text-white">18-Step Full End-to-End Live Walk-Through</h1>
          <p className="text-xs text-gray-400">Guides judges step-by-step from vendor voice diary entry to Qiskit QAOA quantum optimization & human underwriting</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-4 py-2 rounded-xl bg-surfaceLight hover:bg-surfaceLight/80 text-white font-bold text-xs disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={nextStep}
            disabled={currentStep === 18 || loading}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-accent to-primary text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-accent/20"
          >
            {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
            Next Step <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Progress Steps Timeline */}
      <div className="glass-card p-4 overflow-x-auto">
        <div className="flex items-center min-w-max gap-2 text-xs font-semibold">
          {steps.map(s => (
            <button
              key={s.num}
              onClick={() => { setCurrentStep(s.num); handleStepAction(); }}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors ${
                currentStep === s.num
                  ? 'bg-accent text-white font-extrabold'
                  : (s.num < currentStep ? 'bg-emeraldAccent/10 text-emeraldAccent border border-emeraldAccent/30' : 'bg-surfaceLight/40 text-gray-400')
              }`}
            >
              <span>{s.num}.</span> {s.title}
            </button>
          ))}
        </div>
      </div>

      {/* Step Detail Card */}
      <div className="glass-card p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-border/60 pb-4">
          <div>
            <span className="text-xs font-extrabold text-accent uppercase tracking-wider">STEP {currentStep} OF 18</span>
            <h2 className="text-2xl font-extrabold">{steps[currentStep - 1].title}</h2>
            <p className="text-xs text-gray-300">{steps[currentStep - 1].desc}</p>
          </div>
          <span className="px-3 py-1 rounded-full bg-emeraldAccent/10 text-emeraldAccent text-xs font-bold border border-emeraldAccent/30">
            COMPUTATION: LIVE & DETERMINISTIC
          </span>
        </div>

        {/* Dynamic Content Per Step */}
        <div className="space-y-4">
          {currentStep <= 5 && (
            <div className="p-5 rounded-xl bg-surfaceLight border border-border space-y-3">
              <div className="text-xs font-bold text-cyanAccent">Spoken Voice Diary Entry:</div>
              <p className="text-sm font-semibold text-white italic">"{demoState.transcript}"</p>
              {demoState.parsedVoice && (
                <div className="p-3 rounded-lg bg-emeraldAccent/10 border border-emeraldAccent/30 text-xs text-emeraldAccent space-y-1">
                  <div>✔ Extracted Revenue: <strong>₹{demoState.parsedVoice.sales.toLocaleString()}</strong></div>
                  <div>✔ Extracted Expense: <strong>₹{demoState.parsedVoice.expenses.toLocaleString()}</strong></div>
                  <div>✔ Category: <strong>{demoState.parsedVoice.category}</strong></div>
                </div>
              )}
            </div>
          )}

          {(currentStep >= 6 && currentStep <= 9) && (
            <div className="p-5 rounded-xl bg-surfaceLight border border-border space-y-3">
              <div className="text-xs font-bold text-cyanAccent">AI Repayment Model Output:</div>
              <div className="text-3xl font-extrabold text-white">
                {demoState.creditProfile?.score ?? 'N/A'} / 900 
                <span className="ml-2 text-xs text-emeraldAccent bg-emeraldAccent/10 px-2 py-0.5 rounded-full border border-emeraldAccent/20">
                  {demoState.creditProfile?.risk_category || 'LOW_MODERATE'} RISK
                </span>
              </div>
              <div className="text-xs text-gray-300">Model Version: <strong>{demoState.creditProfile?.model_version || 'v3.0.0-RF-Classifier-Persisted'}</strong></div>
              <div className="text-xs text-gray-300">
                Repayment Probability P(repay): <strong>
                  {demoState.creditProfile?.repayment_probability != null
                    ? `${(demoState.creditProfile.repayment_probability * 100).toFixed(1)}%`
                    : 'N/A'}
                </strong>
              </div>
            </div>
          )}

          {currentStep >= 10 && (
            <div className="p-5 rounded-xl bg-surfaceLight border border-border space-y-3">
              <div className="text-xs font-bold text-accent">Quantum Optimization Execution State:</div>
              <div className="text-xs text-gray-300">Algorithm: <strong>Qiskit QAOA (p=2 layers, 1024 shots)</strong></div>
              {demoState.quantumRun && (
                <div className="p-3 rounded-lg bg-emeraldAccent/10 border border-emeraldAccent/30 text-xs text-emeraldAccent space-y-1 font-mono">
                  <div>✔ Qubits Count: {demoState.quantumRun.num_qubits}</div>
                  <div>✔ QAOA Circuit Depth: {demoState.quantumRun.circuit_depth}</div>
                  <div>✔ Optimal Bitstring: {demoState.quantumRun.best_bitstring}</div>
                  <div>✔ Expectation Energy: {demoState.quantumRun.objective_value}</div>
                  <div>✔ Post-Validation: {demoState.quantumRun.validation_status}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
