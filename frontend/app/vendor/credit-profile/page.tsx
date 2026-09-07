'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { ShieldCheck, CheckCircle2, AlertTriangle, BarChart2, ArrowLeft, BrainCircuit, Activity, Database, Gauge, Info, UserCheck, XCircle } from 'lucide-react';
import Link from 'next/link';

const fmtPct = (value: any) => value == null ? '—' : `${(Number(value) * 100).toFixed(1)}%`;
const fmtMoney = (value: any) => value == null ? '—' : `₹${Number(value).toLocaleString('en-IN')}`;

// `useSearchParams()` opts the page into client-side rendering during
// static export, and Next.js requires it to sit behind a Suspense
// boundary or the production build fails outright (this page's build was
// broken before this fix - `next build` errored on this exact route).
export default function CreditProfilePageWrapper() {
  return (
    <Suspense fallback={<div className="brutal-card p-8 text-sm font-black uppercase animate-pulse font-mono">Loading explainable AI profile…</div>}>
      <CreditProfilePage />
    </Suspense>
  );
}

function CreditProfilePage() {
  const { user, loading: authLoading } = useRequireAuth(['VENDOR', 'LENDER', 'ADMIN']);
  const searchParams = useSearchParams();
  const requestedVendorId = searchParams.get('vendor_id');
  const vendorId = user?.role === 'VENDOR' ? user.vendor_id : requestedVendorId;
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Human-review state: only meaningful for a LENDER/ADMIN viewer, so a
  // "review evidence" click from the vendor pool leads directly to a
  // decision, instead of bouncing back to the dashboard to act on it.
  const isReviewer = user?.role === 'LENDER' || user?.role === 'ADMIN';
  const [pendingLoans, setPendingLoans] = useState<any[]>([]);
  const [loansLoading, setLoansLoading] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');
  const [decisionMessage, setDecisionMessage] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !vendorId) return;
    setLoading(true);
    setError(null);
    api.getCreditProfile(vendorId)
      .then(setProfile)
      .catch((err) => setError(err.message || 'Unable to load explainable profile'))
      .finally(() => setLoading(false));
  }, [authLoading, vendorId]);

  useEffect(() => {
    if (authLoading || !vendorId || !isReviewer) return;
    setLoansLoading(true);
    api.getVendorLoans(vendorId)
      .then((loans: any[]) => setPendingLoans((loans || []).filter((l) => ['REQUESTED', 'UNDER_REVIEW'].includes(l.repayment_status))))
      .catch(() => setPendingLoans([]))
      .finally(() => setLoansLoading(false));
  }, [authLoading, vendorId, isReviewer]);

  async function decide(loanId: string, decision: 'APPROVED' | 'REJECTED') {
    setDecisionLoading(true);
    setDecisionMessage(null);
    try {
      await api.underwriteLoan(loanId, decision, decisionNotes || `Human lender decision: ${decision}`);
      setPendingLoans((prev) => prev.filter((l) => l.loan_id !== loanId));
      setDecisionMessage(`Loan ${decision.toLowerCase()}. Recorded to the audit trail.`);
      setDecisionNotes('');
    } catch (err: any) {
      setDecisionMessage(err.message || 'Decision could not be recorded.');
    } finally {
      setDecisionLoading(false);
    }
  }

  if (!authLoading && !vendorId) {
    return <div className="brutal-card p-8 font-mono"><h1 className="text-xl font-black uppercase">Vendor profile unavailable</h1><p className="mt-2 text-sm text-gray-500">Select a vendor from Vendor Discovery to inspect its explainable profile.</p></div>;
  }

  const factors = [...(profile?.positive_factors || []), ...(profile?.watch_factors || [])];
  const features = profile?.features || {};

  return (
    <div className="max-w-6xl mx-auto space-y-6 font-mono">
      <Link href={user?.role === 'VENDOR' ? '/vendor/dashboard' : '/lender/vendors'} className="text-xs font-black uppercase text-gray-500 hover:text-brandRed flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> BACK
      </Link>

      {error && <div className="brutal-card p-4 border-l-8 border-l-brandRed text-sm font-bold">{error}</div>}
      {loading && <div className="brutal-card p-8 text-sm font-black uppercase animate-pulse">Loading explainable AI profile…</div>}

      {profile && !loading && (
        <>
          <div className="brutal-card p-8 border-l-8 border-l-brandRed space-y-5">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
              <div>
                <span className="brutal-badge bg-black text-white dark:bg-white dark:text-black">EXPLAINABLE AI CREDIT PROFILE</span>
                <h1 className="text-3xl font-black uppercase text-black dark:text-white mt-2">{profile.name}</h1>
                <p className="text-xs text-gray-500 font-bold">{profile.business_type} • {profile.location}</p>
                <p className="text-[10px] text-gray-400 mt-2 uppercase">Model-estimated financial intelligence • human decision required</p>
              </div>
              <div className="text-left lg:text-right min-w-[190px]">
                <div className="text-5xl font-black text-black dark:text-white">{profile.score ?? 'N/A'} <span className="text-xs text-gray-500 font-semibold">/ 900</span></div>
                <span className="brutal-badge bg-brandRed text-white mt-2 inline-block">{profile.risk_category || 'UNAVAILABLE'} RISK</span>
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              <Metric icon={<Gauge />} label="Repayment probability" value={fmtPct(profile.repayment_probability)} />
              <Metric icon={<Database />} label="Data quality" value={profile.data_quality_score != null ? `${Number(profile.data_quality_score).toFixed(0)}/100` : '—'} />
              <Metric icon={<Activity />} label="Transactions" value={profile.recent_transaction_count ?? '—'} />
              <Metric icon={<ShieldCheck />} label="Confidence" value={profile.confidence_level || '—'} />
              <Metric icon={<Info />} label="Loan range" value={`${fmtMoney(profile.sustainable_credit_min)} – ${fmtMoney(profile.sustainable_credit_max)}`} />
            </div>

            <div className="p-4 bg-lightSurface2 dark:bg-darkSurface2 border-2 border-black dark:border-white text-xs font-bold text-black dark:text-white">
              <strong className="text-brandRed">[MODEL GOVERNANCE]</strong> Persisted Random Forest classifier: {profile.model_version || 'v3.0.0-RF-Classifier-Persisted'}. This is explainable decision support, not an automated approval.
            </div>
          </div>

          <div className="brutal-card p-6 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b-2 border-black dark:border-white pb-3">
              <h2 className="text-lg font-black uppercase text-black dark:text-white flex items-center gap-2"><BarChart2 className="w-5 h-5 text-brandRed" /> FEATURE CONTRIBUTION MAP</h2>
              <span className="text-[10px] font-black px-2 py-1 border border-black dark:border-white">{profile.explanation_method || 'EXPLANATION'}</span>
            </div>
            <p className="text-xs text-gray-500 font-semibold">Positive values support the repayment class; negative values reduce it. Values are model contributions, not causal claims.</p>
            <div className="space-y-3">
              {(profile.shap_contributions || []).sort((a:any,b:any)=>Math.abs(Number(b.contribution))-Math.abs(Number(a.contribution))).map((c:any)=><div key={c.raw_feature || c.feature}><div className="flex justify-between text-xs font-black"><span>{c.feature}</span><span>{Number(c.contribution) >= 0 ? '+' : ''}{Number(c.contribution).toFixed(1)} pts</span></div><div className="h-2 mt-1 bg-gray-200 dark:bg-gray-800 border border-black dark:border-white"><div className="h-full" style={{width: `${Math.min(100, Math.max(4, Math.abs(Number(c.contribution)) * 2))}%`, backgroundColor: Number(c.contribution) >= 0 ? '#dc2626' : '#111827'}} /></div></div>)}
              {!profile.shap_contributions?.length && <div className="text-xs text-gray-500">No contribution values available.</div>}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="brutal-card p-6 lg:col-span-2 space-y-4">
              <h2 className="text-lg font-black uppercase text-black dark:text-white flex items-center gap-2 border-b-2 border-black dark:border-white pb-3">
                <BrainCircuit className="w-5 h-5 text-brandRed" /> WHY THIS SCORE?
              </h2>
              <p className="text-xs text-gray-500 font-semibold">The explanation below is generated from the same persisted feature pipeline used for scoring. Positive signals increase the model score; watch signals identify areas a human lender should verify.</p>
              <div className="space-y-3">
                {factors.length ? factors.map((fact: any, idx: number) => (
                  <div key={idx} className="p-4 bg-lightSurface2 dark:bg-darkSurface2 border border-black dark:border-white">
                    <div className="flex items-center justify-between gap-3 text-xs font-black">
                      <span className="text-black dark:text-white uppercase">{fact.title}</span>
                      <span className="px-2 py-1 border border-black dark:border-white">{fact.impact || 'signal'}</span>
                    </div>
                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mt-2">{fact.detail}</p>
                  </div>
                )) : <p className="text-xs text-gray-500">No feature-level explanation is available for this profile.</p>}
              </div>
            </div>

            <div className="space-y-6">
              <div className="brutal-card p-6 space-y-4">
                <h2 className="text-sm font-black uppercase border-b-2 border-black dark:border-white pb-3">MODEL INPUT SNAPSHOT</h2>
                {[
                  ['Revenue stability', features.revenue_stability],
                  ['Revenue trend', features.revenue_trend],
                  ['Cashflow score', features.cashflow_score],
                  ['Repayment score', features.repayment_score],
                  ['Business stability', features.business_stability],
                  ['Anomaly score', features.anomaly_score],
                ].map(([label, value]) => <div key={String(label)} className="flex justify-between gap-3 text-xs"><span className="text-gray-500">{label}</span><strong>{value == null ? '—' : Number(value).toFixed(3)}</strong></div>)}
              </div>
              <div className="brutal-card p-6 space-y-3 border-t-4 border-t-brandRed">
                <h2 className="text-sm font-black uppercase flex items-center gap-2"><UserCheck className="w-4 h-4 text-brandRed" /> HUMAN REVIEW</h2>
                {!isReviewer && (
                  <p className="text-xs text-gray-600 dark:text-gray-300 font-semibold">AI can surface evidence and risk signals, but a lender must verify affordability, documentation, consent, and repayment capacity before approving a loan.</p>
                )}
                {isReviewer && loansLoading && (
                  <p className="text-xs text-gray-500 font-semibold uppercase">Checking pending loan requests...</p>
                )}
                {isReviewer && !loansLoading && pendingLoans.length === 0 && (
                  <p className="text-xs text-gray-600 dark:text-gray-300 font-semibold">No pending loan request for this vendor right now.</p>
                )}
                {isReviewer && pendingLoans.map((loan) => (
                  <div key={loan.loan_id} className="p-3 bg-lightSurface2 dark:bg-darkSurface2 border border-black dark:border-white space-y-2">
                    <div className="flex justify-between text-xs font-black">
                      <span>Requested</span>
                      <span className="text-brandRed">{fmtMoney(loan.principal)}</span>
                    </div>
                    <div className="text-[10px] text-gray-500 uppercase">Status: {loan.repayment_status}</div>
                    <textarea
                      value={decisionNotes}
                      onChange={(e) => setDecisionNotes(e.target.value)}
                      placeholder="Optional underwriting notes..."
                      className="w-full text-xs p-2 border border-black dark:border-white bg-transparent font-mono"
                      rows={2}
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={decisionLoading}
                        onClick={() => decide(loan.loan_id, 'APPROVED')}
                        className="flex-1 py-2 bg-black text-white dark:bg-white dark:text-black text-[10px] font-black uppercase flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-brandRed" /> Approve
                      </button>
                      <button
                        disabled={decisionLoading}
                        onClick={() => decide(loan.loan_id, 'REJECTED')}
                        className="flex-1 py-2 border-2 border-brandRed text-brandRed text-[10px] font-black uppercase flex items-center justify-center gap-1 disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5" /> Reject
                      </button>
                    </div>
                  </div>
                ))}
                {decisionMessage && <p className="text-[10px] font-bold text-brandRed uppercase">{decisionMessage}</p>}
              </div>
            </div>
          </div>

          {profile.disclaimer && <div className="text-[10px] font-semibold text-gray-500 normal-case brutal-card p-4">{profile.disclaimer}</div>}
        </>
      )}
    </div>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return <div className="p-3 border border-black dark:border-white bg-lightSurface2 dark:bg-darkSurface2"><div className="flex items-center gap-1 text-[9px] uppercase text-gray-500 font-black">{icon}<span>{label}</span></div><div className="text-sm font-black mt-1 truncate">{value}</div></div>;
}
