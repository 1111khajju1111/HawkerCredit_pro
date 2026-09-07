'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import {
  ClipboardList, Loader2, ShieldCheck, ArrowRight, CheckCircle2, XCircle,
  Flag, ExternalLink, Inbox,
} from 'lucide-react';

const PENDING_STATUSES = ['REQUESTED', 'UNDER_REVIEW'];

function riskBadgeClasses(riskCategory?: string | null) {
  switch ((riskCategory || '').toUpperCase()) {
    case 'LOW':
      return 'text-emeraldAccent bg-emeraldAccent/10 border-emeraldAccent/20';
    case 'HIGH':
      return 'text-red-400 bg-red-400/10 border-red-400/20';
    case 'MODERATE':
    case 'MEDIUM':
      return 'text-warning bg-warning/10 border-warning/20';
    default:
      return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
  }
}

function statusBadgeClasses(status: string) {
  switch (status) {
    case 'ACTIVE':
    case 'COMPLETED':
      return 'text-emeraldAccent bg-emeraldAccent/10 border-emeraldAccent/20';
    case 'REJECTED':
    case 'DEFAULTED':
      return 'text-red-400 bg-red-400/10 border-red-400/20';
    case 'UNDER_REVIEW':
      return 'text-warning bg-warning/10 border-warning/20';
    default:
      return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
  }
}

function formatCurrency(n?: number | null) {
  if (n === null || n === undefined) return 'N/A';
  return `₹${Math.round(n).toLocaleString('en-IN')}`;
}

export default function HumanReviewPage() {
  const { loading: authLoading } = useRequireAuth(['LENDER', 'ADMIN']);
  const [loans, setLoans] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [notesByLoan, setNotesByLoan] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [showDecided, setShowDecided] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading) return;
    loadAll();
  }, [authLoading]);

  async function loadAll() {
    setLoading(true);
    setError('');
    try {
      const [lList, vList] = await Promise.all([api.getLoans(), api.getVendors()]);
      setLoans(lList);
      setVendors(vList);
    } catch (err: any) {
      setError(err.message || 'Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  }

  const vendorMap = useMemo(() => {
    const m: Record<string, any> = {};
    vendors.forEach((v) => { m[v.vendor_id] = v; });
    return m;
  }, [vendors]);

  const pending = loans.filter((l) => PENDING_STATUSES.includes(l.repayment_status));
  const decided = loans.filter((l) => !PENDING_STATUSES.includes(l.repayment_status));

  async function decide(loanId: string, decision: string) {
    setSubmitting(loanId + decision);
    setError('');
    try {
      await api.underwriteLoan(loanId, decision, notesByLoan[loanId] || undefined);
      setLoans((prev) => prev.map((l) => (l.loan_id === loanId ? { ...l, repayment_status: decision, human_notes: notesByLoan[loanId] || l.human_notes } : l)));
    } catch (err: any) {
      setError(err.message || 'Decision failed to save.');
    } finally {
      setSubmitting(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 glass-card p-6 border-l-4 border-l-warning">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ClipboardList className="w-6 h-6 text-warning" /> Human Review Queue
          </h1>
          <p className="text-xs text-gray-400">Every AI/quantum recommendation requires a human lender decision before capital moves</p>
        </div>
        <div className="text-xs text-gray-400">
          <span className="text-warning font-extrabold text-lg">{pending.length}</span> awaiting decision
        </div>
      </div>

      {error && (
        <div className="glass-card p-4 border-l-4 border-l-red-400 text-xs text-red-400">{error}</div>
      )}

      {loading ? (
        <div className="glass-card p-10 flex items-center justify-center gap-2 text-sm text-gray-400">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading review queue...
        </div>
      ) : pending.length === 0 ? (
        <div className="glass-card p-10 flex flex-col items-center justify-center gap-2 text-sm text-gray-400">
          <Inbox className="w-6 h-6 text-gray-500" />
          No loan applications are currently awaiting review.
        </div>
      ) : (
        <div className="space-y-4">
          {pending.map((l) => {
            const v = vendorMap[l.vendor_id];
            const hasScore = v?.score !== null && v?.score !== undefined;
            const busyKey = submitting && submitting.startsWith(l.loan_id) ? submitting : null;
            return (
              <div key={l.loan_id} className="glass-card p-5 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold text-white">{v ? v.name : l.vendor_id}</span>
                      {v && (
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${riskBadgeClasses(v.risk_category)}`}>
                          {hasScore ? `Score: ${v.score} (${v.risk_category})` : 'No Score Yet'}
                        </span>
                      )}
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${statusBadgeClasses(l.repayment_status)}`}>
                        {l.repayment_status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{v ? `${v.business_type} • ${v.location}` : ''}</p>
                  </div>
                  {v && (
                    <Link
                      href={`/vendor/credit-profile?vendor_id=${v.vendor_id}`}
                      className="text-xs text-primary font-bold hover:underline flex items-center gap-1 shrink-0"
                    >
                      Full Explainable Profile <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-lg bg-surfaceLight/60 border border-border">
                    <div className="text-gray-400">Requested Principal</div>
                    <div className="text-white font-bold text-sm">{formatCurrency(l.principal)}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-surfaceLight/60 border border-border">
                    <div className="text-gray-400">Interest Rate</div>
                    <div className="text-white font-bold text-sm">{l.interest_rate}%</div>
                  </div>
                  <div className="p-3 rounded-lg bg-surfaceLight/60 border border-border">
                    <div className="text-gray-400">Due Date</div>
                    <div className="text-white font-bold text-sm">{new Date(l.due_date).toLocaleDateString()}</div>
                  </div>
                  <div className="p-3 rounded-lg bg-surfaceLight/60 border border-border">
                    <div className="text-gray-400">Repayment Probability</div>
                    <div className="text-cyanAccent font-bold text-sm">{hasScore ? `${Math.round(v.repayment_probability * 100)}%` : 'N/A'}</div>
                  </div>
                </div>

                <textarea
                  placeholder="Add underwriting notes (optional, visible in audit trail)..."
                  value={notesByLoan[l.loan_id] || ''}
                  onChange={(e) => setNotesByLoan((prev) => ({ ...prev, [l.loan_id]: e.target.value }))}
                  className="w-full p-2.5 rounded-lg bg-surfaceLight border border-border text-xs text-white focus:outline-none focus:border-primary resize-none"
                  rows={2}
                />

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => decide(l.loan_id, 'ACTIVE')}
                    disabled={!!submitting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emeraldAccent/15 border border-emeraldAccent/30 text-emeraldAccent text-xs font-bold hover:bg-emeraldAccent/25 transition-colors disabled:opacity-50"
                  >
                    {busyKey === l.loan_id + 'ACTIVE' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />} Approve
                  </button>
                  <button
                    onClick={() => decide(l.loan_id, 'REJECTED')}
                    disabled={!!submitting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-400/15 border border-red-400/30 text-red-400 text-xs font-bold hover:bg-red-400/25 transition-colors disabled:opacity-50"
                  >
                    {busyKey === l.loan_id + 'REJECTED' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />} Reject
                  </button>
                  {l.repayment_status !== 'UNDER_REVIEW' && (
                    <button
                      onClick={() => decide(l.loan_id, 'UNDER_REVIEW')}
                      disabled={!!submitting}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-warning/15 border border-warning/30 text-warning text-xs font-bold hover:bg-warning/25 transition-colors disabled:opacity-50"
                    >
                      {busyKey === l.loan_id + 'UNDER_REVIEW' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Flag className="w-3.5 h-3.5" />} Flag for Further Review
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && decided.length > 0 && (
        <div className="glass-card p-6 space-y-3">
          <button onClick={() => setShowDecided((s) => !s)} className="flex items-center justify-between w-full text-left">
            <h2 className="text-sm font-bold text-gray-300">Decided Loans ({decided.length})</h2>
            <ArrowRight className={`w-4 h-4 text-gray-400 transition-transform ${showDecided ? 'rotate-90' : ''}`} />
          </button>
          {showDecided && (
            <div className="space-y-2 pt-2">
              {decided.map((l) => {
                const v = vendorMap[l.vendor_id];
                return (
                  <div key={l.loan_id} className="flex items-center justify-between p-3 rounded-lg bg-surfaceLight/40 border border-border/40 text-xs">
                    <div>
                      <span className="text-white font-semibold">{v ? v.name : l.vendor_id}</span>
                      <span className="text-gray-400"> • {formatCurrency(l.principal)}</span>
                      {l.human_notes && <p className="text-gray-500 italic mt-0.5">"{l.human_notes}"</p>}
                    </div>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${statusBadgeClasses(l.repayment_status)}`}>
                      {l.repayment_status}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
