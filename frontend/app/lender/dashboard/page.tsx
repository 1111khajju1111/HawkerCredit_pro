'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { ShieldCheck, Users, Sparkles, CheckCircle2, ArrowRight, AlertTriangle, UserCheck } from 'lucide-react';

export default function LenderDashboard() {
  const { loading: authLoading } = useRequireAuth(['LENDER', 'ADMIN']);
  const [vendors, setVendors] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewLoading, setReviewLoading] = useState(false);

  async function load() {
    try {
      const [s, loans, allVendors] = await Promise.all([api.getLenderSummary(), api.getLoans(), api.getVendors()]);
      setSummary(s); setVendors(allVendors || s.vendors || []);
      setReviews((loans || []).filter((l: any) => ['REQUESTED', 'UNDER_REVIEW'].includes(l.repayment_status)));
    } catch (err) { console.error(err); }
  }
  useEffect(() => { if (!authLoading) load(); }, [authLoading]);

  async function decide(loanId: string, decision: 'APPROVED' | 'REJECTED') {
    setReviewLoading(true);
    try { await api.underwriteLoan(loanId, decision, `Human lender decision: ${decision}`); await load(); }
    catch (err) { console.error(err); }
    finally { setReviewLoading(false); }
  }

  return <div className="space-y-6">
    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 glass-card p-6 border-l-4 border-l-accent">
      <div><h1 className="text-2xl font-bold flex items-center gap-2"><ShieldCheck className="w-6 h-6 text-accent" /> Institutional Lender Portfolio Intelligence</h1><p className="text-xs text-gray-400">Evidence-first credit intelligence, quantum-assisted allocation and human underwriting.</p></div>
      <div className="flex items-center gap-3"><Link href="/lender/portfolio/optimizer" className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-accent via-primary to-cyanAccent text-white font-bold text-xs flex items-center gap-2"><Sparkles className="w-4 h-4" /> Run Quantum Optimizer</Link><Link href="/lender/benchmark" className="px-4 py-2.5 rounded-xl bg-surfaceLight text-white font-semibold text-xs border border-border">Quantum vs Classical</Link></div>
    </div>

    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card label="Total Vendor Pool" value={`${summary?.total_vendors ?? 0} Vendors`} sub="Synthetic demo pool • target 100" />
      <Card label="Available Capital Budget" value="₹10,00,000" sub="Configured portfolio pool" />
      <Card label="Avg Credit Intelligence Score" value={summary?.avg_credit_score != null ? Math.round(summary.avg_credit_score) : '—'} sub="Persisted model scores" />
      <Card label="Pending Human Reviews" value={summary?.pending_human_reviews ?? 0} sub="Requires human lender action" warning />
    </div>

    <div className="glass-card p-6 space-y-4"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Human Underwriting Queue</h2><p className="text-xs text-gray-400">AI recommends; a lender decides. Every decision is persisted to the audit trail.</p></div><UserCheck className="w-5 h-5 text-warning" /></div>
      {reviews.length === 0 ? <div className="p-5 rounded-xl bg-surfaceLight/50 border border-border text-xs text-gray-400">No pending reviews. New REQUESTED or UNDER_REVIEW loans will appear here.</div> : <div className="space-y-3">{reviews.slice(0,8).map((loan:any) => { const v=vendors.find(x=>x.vendor_id===loan.vendor_id); return <div key={loan.loan_id} className="p-4 rounded-xl bg-surfaceLight/60 border border-border flex flex-col md:flex-row md:items-center justify-between gap-3"><div><div className="text-sm font-bold text-white">{v?.name || `Vendor ${loan.vendor_id.slice(0,8)}`}</div><div className="text-[11px] text-gray-400">{v?.business_type || 'Vendor'} • {v?.risk_category || 'Risk —'} • Score {v?.score != null ? Math.round(v.score) : '—'}</div><div className="text-xs mt-1 text-cyanAccent">Requested: ₹{Number(loan.principal).toLocaleString('en-IN')}</div></div><div className="flex gap-2"><Link href={`/vendor/credit-profile?vendor_id=${encodeURIComponent(loan.vendor_id)}`} className="px-3 py-2 rounded-lg border border-border text-xs font-bold text-white">Review evidence</Link><button disabled={reviewLoading} onClick={()=>decide(loan.loan_id,'APPROVED')} className="px-3 py-2 rounded-lg bg-emeraldAccent/20 border border-emeraldAccent/40 text-emeraldAccent text-xs font-black">Approve</button><button disabled={reviewLoading} onClick={()=>decide(loan.loan_id,'REJECTED')} className="px-3 py-2 rounded-lg bg-brandRed/10 border border-brandRed/40 text-brandRed text-xs font-black">Reject</button></div></div>})}</div>}
    </div>

    <div className="glass-card p-6 space-y-4"><div className="flex items-center justify-between"><h2 className="text-lg font-bold flex items-center gap-2"><Users className="w-5 h-5 text-primary" /> Eligible Candidate Vendors</h2><Link href="/lender/vendors" className="text-xs text-primary font-bold">Browse all vendors <ArrowRight className="inline w-3 h-3" /></Link></div><div className="grid grid-cols-1 md:grid-cols-3 gap-4">{vendors.slice(0,6).map((v:any)=><div key={v.vendor_id} className="p-4 rounded-xl bg-surfaceLight/60 border border-border"><div className="flex justify-between"><span className="text-sm font-bold text-white">{v.name}</span><span className="text-xs font-bold text-emeraldAccent">{v.score != null ? `Score ${Math.round(v.score)}` : 'Score —'}</span></div><p className="text-xs text-gray-400 mt-1">{v.business_type} • {v.location}</p><div className="flex justify-between pt-2 mt-2 border-t border-border/40 text-xs"><span className="text-gray-400">Requested</span><strong className="text-cyanAccent">{v.requested_loan != null ? `₹${Number(v.requested_loan).toLocaleString('en-IN')}` : '—'}</strong></div></div>)}</div></div>

    <div className="p-4 rounded-xl bg-accent/5 border border-accent/20 text-xs text-gray-400"><CheckCircle2 className="inline w-4 h-4 text-emeraldAccent mr-2" /> <strong className="text-white">Synthetic demo disclosure:</strong> vendor/lender records and repayment outcomes are synthetic and are for product demonstration only; they are not real credit-bureau data or validated lending performance.</div>
  </div>;
}
function Card({label,value,sub,warning=false}:{label:string;value:any;sub:string;warning?:boolean}) { return <div className="glass-card p-5 space-y-1"><div className="text-xs font-semibold text-gray-400">{label}</div><div className={`text-3xl font-extrabold ${warning?'text-warning':'text-white'}`}>{value}</div><p className="text-[11px] text-gray-400">{sub}</p></div>; }
