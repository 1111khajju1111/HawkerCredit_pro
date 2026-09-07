'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useAuth, useRequireAuth } from '@/lib/auth';
import { Mic, Receipt, Plus, TrendingUp, AlertTriangle, ShieldCheck, FileText, CheckCircle2, ArrowUpRight, DollarSign, Wallet } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function VendorDashboard() {
  const router = useRouter();
  const { logout } = useAuth();
  const { user, loading: authLoading } = useRequireAuth(['VENDOR']);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user?.vendor_id) return;

    async function loadData(vendorId: string) {
      try {
        const profData = await api.getCreditProfile(vendorId);
        setProfile(profData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData(user.vendor_id as string);
  }, [authLoading, user]);

  const chartData = [
    { day: 'MON', sales: 4200, expense: 1800 },
    { day: 'TUE', sales: 4800, expense: 2100 },
    { day: 'WED', sales: 3900, expense: 1500 },
    { day: 'THU', sales: 5200, expense: 2300 },
    { day: 'FRI', sales: 5800, expense: 2400 },
    { day: 'SAT', sales: 6400, expense: 2900 },
    { day: 'SUN', sales: 5100, expense: 2200 }
  ];

  if (authLoading || !user || loading) {
    return <div className="p-8 text-center font-mono font-bold uppercase">LOADING VENDOR DASHBOARD...</div>;
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Top Banner */}
      <div className="brutal-card p-6 border-l-8 border-l-brandRed flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span className="brutal-badge bg-black text-white dark:bg-white dark:text-black font-bold">VENDOR PORTAL</span>
          <h1 className="text-3xl font-black uppercase text-black dark:text-white mt-1">{profile?.name || 'Ramesh Kumar'}</h1>
          <p className="text-xs text-gray-500 font-semibold">{profile?.business_type} • {profile?.location || 'Sarojini Nagar, New Delhi'}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/vendor/voice-entry" className="brutal-btn bg-brandRed text-white px-4 py-2.5 text-xs flex items-center gap-1.5">
            <Mic className="w-4 h-4" /> VOICE ENTRY
          </Link>
          <Link href="/vendor/receipt-entry" className="brutal-btn bg-white text-black dark:bg-black dark:text-white px-4 py-2.5 text-xs flex items-center gap-1.5">
            <Receipt className="w-4 h-4 text-brandRed" /> RECEIPT OCR
          </Link>
          <Link href="/vendor/credit-profile" className="brutal-btn bg-white text-black dark:bg-black dark:text-white px-4 py-2.5 text-xs flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-brandRed" /> CREDIT PROFILE
          </Link>
          <button
            onClick={() => { logout(); router.push('/login'); }}
            className="brutal-btn bg-white text-black dark:bg-black dark:text-white px-4 py-2.5 text-xs"
          >
            LOGOUT
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Credit Score Gauge */}
        <div className="brutal-card p-5 space-y-2">
          <div className="text-xs font-black uppercase text-gray-500">HAWKERCREDIT SCORE</div>
          <div className="flex items-baseline justify-between">
            <span className="text-4xl font-black text-black dark:text-white">{profile?.score ?? 'N/A'}</span>
            <span className="brutal-badge bg-brandRed text-white">
              {profile?.risk_category ?? 'N/A'}
            </span>
          </div>
          <p className="text-[10px] font-bold text-gray-500 uppercase">
            REPAYMENT PROB: {profile?.repayment_probability != null ? `${(profile.repayment_probability * 100).toFixed(0)}%` : 'N/A'}
          </p>
        </div>

        {/* Data Quality */}
        <div className="brutal-card p-5 space-y-2">
          <div className="text-xs font-black uppercase text-gray-500">DATA QUALITY RATING</div>
          <div className="flex items-baseline justify-between">
            <span className="text-4xl font-black text-brandRed">{profile?.data_quality_score ?? 'N/A'}/100</span>
            <span className="brutal-badge bg-black text-white dark:bg-white dark:text-black">
              {profile?.confidence_level ?? 'N/A'}
            </span>
          </div>
          <p className="text-[10px] font-bold text-gray-500 uppercase">60 DAYS ACTIVE DIARY ENTRIES</p>
        </div>

        {/* Net Cashflow */}
        <div className="brutal-card p-5 space-y-2">
          <div className="text-xs font-black uppercase text-gray-500">ESTIMATED WEEKLY CASHFLOW</div>
          <div className="text-3xl font-black text-black dark:text-white">₹18,400</div>
          <p className="text-[10px] font-bold text-brandRed flex items-center gap-1 uppercase">
            <TrendingUp className="w-3 h-3" /> +12% VS LAST WEEK
          </p>
        </div>

        {/* Sustainable Credit Range */}
        <div className="brutal-card p-5 space-y-2">
          <div className="text-xs font-black uppercase text-gray-500">AFFORDABILITY CREDIT RANGE</div>
          <div className="text-2xl font-black text-brandRed">₹20K – ₹35K</div>
          <p className="text-[10px] font-bold text-gray-500 uppercase">MODEL-ESTIMATED LOAN LIMIT</p>
        </div>
      </div>

      {/* Chart & AI Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="brutal-card p-6 lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between border-b-2 border-black dark:border-white pb-3">
            <h2 className="text-lg font-black uppercase text-black dark:text-white">REVENUE & EXPENSE TREND</h2>
            <div className="flex items-center gap-4 text-xs font-bold uppercase">
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-black dark:bg-white border border-black inline-block"></span> REVENUE</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-3 bg-brandRed inline-block"></span> EXPENSE</span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <XAxis dataKey="day" stroke="currentColor" fontSize={11} fontFamily="monospace" />
                <YAxis stroke="currentColor" fontSize={11} fontFamily="monospace" />
                <Tooltip contentStyle={{ backgroundColor: '#000', color: '#fff', border: '2px solid #dc2626' }} />
                <Area type="monotone" dataKey="sales" stroke="#000" fill="#000" fillOpacity={0.15} />
                <Area type="monotone" dataKey="expense" stroke="#dc2626" fill="#dc2626" fillOpacity={0.2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="brutal-card p-6 space-y-4">
          <h2 className="text-lg font-black uppercase text-black dark:text-white flex items-center gap-2 border-b-2 border-black dark:border-white pb-3">
            <ShieldCheck className="w-5 h-5 text-brandRed" /> AI CREDIT TIPS
          </h2>
          <div className="space-y-3 text-xs font-semibold">
            <div className="p-3 bg-lightSurface2 dark:bg-darkSurface2 border border-black dark:border-white space-y-1">
              <div className="font-black text-black dark:text-white uppercase flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-brandRed" /> HIGH DAILY CONTINUITY
              </div>
              <p className="text-gray-600 dark:text-gray-300">Logged sales 6 out of 7 days this week. Keeps your stability score high.</p>
            </div>
            <div className="p-3 bg-lightSurface2 dark:bg-darkSurface2 border border-black dark:border-white space-y-1">
              <div className="font-black text-brandRed uppercase flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> STOCK PURCHASE VOLATILITY
              </div>
              <p className="text-gray-600 dark:text-gray-300">Expense ratio spiked on Thursday. Consolidate wholesale Mandi orders.</p>
            </div>
          </div>
          <Link href="/vendor/coach" className="block text-center text-xs font-black text-brandRed uppercase hover:underline pt-2">
            OPEN AI FINANCIAL COACH →
          </Link>
        </div>
      </div>
    </div>
  );
}
