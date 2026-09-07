'use client';

import Link from 'next/link';
import { ArrowRight, Sparkles, CheckCircle, ShieldCheck, Cpu, Activity, Lock } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="space-y-12 py-4">
      {/* Hero Section */}
      <section className="brutal-card p-8 md:p-12 space-y-6 text-left border-l-8 border-l-brandRed">
        <div className="inline-block brutal-badge bg-black text-white dark:bg-white dark:text-black font-mono font-bold">
          AI + QUANTUM // STREET VENDOR FINANCIAL INTELLIGENCE
        </div>

        <h1 className="text-4xl md:text-6xl font-black font-mono tracking-tight leading-none uppercase">
          MAKING INVISIBLE STREET BUSINESS ACTIVITY <br className="hidden md:inline" />
          <span className="text-brandRed bg-black dark:bg-white text-white dark:text-black px-2 py-1 inline-block mt-2">
            MEASURABLE & ALLOCABLE
          </span>
        </h1>

        <p className="text-black dark:text-white text-base md:text-lg max-w-3xl font-semibold leading-relaxed">
          HawkerCredit Quantum converts consented everyday business diary entries of informal street vendors into explainable alternative credit profiles using classical AI/ML, and applies QAOA quantum optimization for constrained lender portfolio allocation.
        </p>

        <div className="flex flex-wrap items-center gap-4 pt-4 font-mono">
          <Link href="/demo" className="brutal-btn bg-brandRed text-white px-6 py-3 text-sm flex items-center gap-2">
            EXPLORE 18-STEP LIVE DEMO <ArrowRight className="w-4 h-4" />
          </Link>
          <Link href="/vendor/dashboard" className="brutal-btn bg-white text-black dark:bg-black dark:text-white px-6 py-3 text-sm">
            VENDOR PORTAL
          </Link>
          <Link href="/lender/dashboard" className="brutal-btn bg-white text-black dark:bg-black dark:text-white px-6 py-3 text-sm">
            LENDER DASHBOARD
          </Link>
        </div>
      </section>

      {/* Problem vs Solution Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-8 font-mono">
        <div className="brutal-card p-6 space-y-4 border-l-8 border-l-black dark:border-l-white">
          <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight flex items-center gap-2">
            <span className="w-3 h-3 bg-black dark:bg-white inline-block"></span> TRADITIONAL CREDIT FRICTION
          </h2>
          <ul className="space-y-3 text-xs font-semibold text-black dark:text-gray-300">
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✕</span> Street vendors generate high daily turnover but lack formal bank statements or CIBIL history.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✕</span> Lenders perceive informal vendors as high-risk, charging prohibitive interest rates.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✕</span> Institutional capital allocation across hundreds of vendors suffers from sub-optimal heuristic selection.
            </li>
          </ul>
        </div>

        <div className="brutal-card p-6 space-y-4 border-l-8 border-l-brandRed">
          <h2 className="text-xl font-black text-black dark:text-white uppercase tracking-tight flex items-center gap-2">
            <span className="w-3 h-3 bg-brandRed inline-block"></span> HAWKERCREDIT PARADIGM
          </h2>
          <ul className="space-y-3 text-xs font-semibold text-black dark:text-gray-300">
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✓</span> <strong>CONSENTED ACTIVITY:</strong> Vendors log sales via voice & receipts in daily business diaries.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✓</span> <strong>EXPLAINABLE AI:</strong> Scikit-Learn model outputs transparent 300-900 credit score & data quality rating.
            </li>
            <li className="flex items-start gap-2">
              <span className="text-brandRed font-black">✓</span> <strong>QUANTUM PORTFOLIO:</strong> QUBO + QAOA on Qiskit optimizes lender capital allocation under strict risk limits.
            </li>
          </ul>
        </div>
      </section>

      {/* Architecture Pipeline Visualizer */}
      <section className="brutal-card p-8 space-y-6 font-mono">
        <div className="border-b-2 border-black dark:border-white pb-4">
          <h2 className="text-2xl font-black uppercase text-black dark:text-white">END-TO-END HYBRID CLASSICAL-QUANTUM PIPELINE</h2>
          <p className="text-xs text-brandRed font-bold uppercase mt-1">Strict separation of AI financial intelligence, quantum optimization, and human underwriting</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 pt-2 text-center text-xs">
          <div className="brutal-card p-4 space-y-1">
            <div className="text-brandRed font-black">STAGE 1</div>
            <div className="font-bold text-black dark:text-white uppercase">VENDOR ACTIVITY</div>
            <div className="text-[10px] text-gray-500">VOICE / DIARY / OCR</div>
          </div>
          <div className="brutal-card p-4 space-y-1">
            <div className="text-brandRed font-black">STAGE 2</div>
            <div className="font-bold text-black dark:text-white uppercase">FEATURE ENGINE</div>
            <div className="text-[10px] text-gray-500">12+ ML FEATURES</div>
          </div>
          <div className="brutal-card p-4 space-y-1">
            <div className="text-brandRed font-black">STAGE 3</div>
            <div className="font-bold text-black dark:text-white uppercase">EXPLAINABLE AI</div>
            <div className="text-[10px] text-gray-500">ALTERNATIVE SCORE</div>
          </div>
          <div className="brutal-card p-4 space-y-1">
            <div className="text-brandRed font-black">STAGE 4</div>
            <div className="font-bold text-black dark:text-white uppercase">QUBO MATRIX</div>
            <div className="text-[10px] text-gray-500">BINARY VARIABLES</div>
          </div>
          <div className="brutal-card p-4 space-y-1">
            <div className="text-brandRed font-black">STAGE 5</div>
            <div className="font-bold text-black dark:text-white uppercase">QAOA SOLVER</div>
            <div className="text-[10px] text-gray-500">QISKIT AER SIM</div>
          </div>
          <div className="brutal-card-red p-4 space-y-1">
            <div className="font-black">STAGE 6</div>
            <div className="font-bold uppercase">HUMAN REVIEW</div>
            <div className="text-[10px]">UNDERWRITING</div>
          </div>
        </div>
      </section>
    </div>
  );
}
