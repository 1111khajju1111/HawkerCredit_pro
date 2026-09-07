'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { Search, ShieldCheck, ArrowRight, Users, AlertTriangle, RefreshCw } from 'lucide-react';

const money = (v: any) => v == null ? '—' : `₹${Number(v).toLocaleString('en-IN')}`;

export default function VendorDiscoveryPage() {
  const { loading: authLoading } = useRequireAuth(['LENDER', 'ADMIN']);
  const [vendors, setVendors] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError(null);
    try { setVendors(await api.getVendors()); }
    catch (err: any) { setError(err.message || 'Unable to load vendor pool'); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (!authLoading) load(); }, [authLoading]);

  const filtered = vendors.filter(v => `${v.name} ${v.business_type} ${v.location}`.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Users className="w-5 h-5 text-primary" /> Vendor Discovery & Explainable Intelligence</h1>
          <p className="text-xs text-gray-400">Persisted synthetic demo pool with model score, repayment probability, data quality and human-review state.</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <div className="w-full md:w-72 relative"><input type="text" placeholder="Search name, business or location…" value={search} onChange={e => setSearch(e.target.value)} className="w-full p-2.5 pl-9 rounded-xl bg-surfaceLight border border-border text-xs text-white focus:outline-none focus:border-primary" /><Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" /></div>
          <button onClick={load} disabled={loading} className="px-3 rounded-xl border border-border bg-surfaceLight text-white"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
      </div>

      {error && <div className="glass-card p-4 text-xs font-bold text-red-400">{error}</div>}
      {!loading && <div className="text-xs text-gray-400">Showing <strong className="text-white">{filtered.length}</strong> of <strong className="text-white">{vendors.length}</strong> vendors.</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(v => (
          <div key={v.vendor_id} className="glass-card p-5 space-y-4 hover:border-primary/50 transition-colors">
            <div className="flex items-start justify-between gap-3">
              <div><div className="text-sm font-bold text-white">{v.name}</div><p className="text-[11px] text-gray-400 mt-1">{v.business_type} • {v.location}</p></div>
              <span className="text-xs font-black text-emeraldAccent bg-emeraldAccent/10 px-2 py-1 rounded-full border border-emeraldAccent/20">{v.score != null ? `Score ${Math.round(v.score)}` : 'Score —'}</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              <Stat label="Repayment" value={v.repayment_probability != null ? `${(v.repayment_probability * 100).toFixed(0)}%` : '—'} />
              <Stat label="Data quality" value={v.data_quality_score != null ? `${Number(v.data_quality_score).toFixed(0)}/100` : '—'} />
              <Stat label="Risk" value={v.risk_category || '—'} />
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-border/60 text-xs"><span className="text-gray-400">Requested loan</span><strong className="text-cyanAccent">{money(v.requested_loan)}</strong></div>
            {v.pending_human_review && <div className="flex items-center gap-1.5 text-[10px] font-bold text-warning"><AlertTriangle className="w-3.5 h-3.5" /> HUMAN REVIEW REQUIRED</div>}
            <Link href={`/vendor/credit-profile?vendor_id=${encodeURIComponent(v.vendor_id)}`} className="block text-center py-2.5 rounded-lg bg-surfaceLight hover:bg-surfaceLight/80 text-xs font-bold text-white transition-colors">View Explainable Profile <ArrowRight className="inline w-3.5 h-3.5 ml-1" /></Link>
          </div>
        ))}
      </div>
    </div>
  );
}
function Stat({label,value}:{label:string;value:string}) { return <div className="p-2 rounded-lg bg-surfaceLight/60 border border-border"><div className="text-gray-500 uppercase">{label}</div><div className="font-black text-white mt-0.5 truncate">{value}</div></div>; }
