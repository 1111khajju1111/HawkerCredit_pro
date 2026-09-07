'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { ShieldCheck, Users, Cpu, Database, Activity, FileText } from 'lucide-react';

export default function AdminDashboard() {
  const { loading: authLoading } = useRequireAuth(['ADMIN']);
  const [metrics, setMetrics] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    async function load() {
      try {
        const m = await api.getAdminMetrics();
        const logs = await api.getAuditLogs();
        setMetrics(m);
        setAuditLogs(logs);
        setLoadError(null);
      } catch (err: any) {
        console.error(err);
        // No fabricated numbers on failure -- surface the failure itself instead.
        setLoadError(err?.message || 'Unable to reach the backend');
      }
    }
    load();
  }, [authLoading]);

  const model = metrics?.ai_model_monitoring;
  const hasTrainedModel = model && model.accuracy != null;

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 border-l-4 border-l-emeraldAccent flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emeraldAccent" /> System Administration & Model Governance
          </h1>
          <p className="text-xs text-gray-400">Monitor platform health, AI model metrics, quantum job status, and security audit trail</p>
        </div>
        {/* Reflects whether the metrics call actually succeeded -- never a
            permanent claim independent of the backend's real response. */}
        <div className={`px-3 py-1.5 rounded-full font-bold text-xs border ${
          loadError
            ? 'bg-red-500/10 text-red-400 border-red-500/30'
            : metrics
              ? 'bg-emeraldAccent/10 text-emeraldAccent border-emeraldAccent/30'
              : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
        }`}>
          {loadError ? 'BACKEND UNREACHABLE' : metrics ? 'BACKEND REACHABLE' : 'CHECKING...'}
        </div>
      </div>

      {loadError && (
        <div className="glass-card p-4 text-xs font-bold text-red-400">{loadError}</div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="glass-card p-5 space-y-1">
          <div className="text-xs font-semibold text-gray-400">Total Registered Users</div>
          <div className="text-3xl font-extrabold text-white">{metrics?.system_metrics?.total_users ?? 'N/A'}</div>
          <p className="text-[11px] text-gray-400">Vendors, Lenders & Admins</p>
        </div>
        <div className="glass-card p-5 space-y-1">
          <div className="text-xs font-semibold text-gray-400">Seeded Vendor Profiles</div>
          <div className="text-3xl font-extrabold text-cyanAccent">{metrics?.system_metrics?.total_vendors ?? 'N/A'}</div>
          <p className="text-[11px] text-gray-400">60-day financial diaries</p>
        </div>
        <div className="glass-card p-5 space-y-2">
          <div className="text-xs font-semibold text-gray-400">AI Model Performance</div>
          <div className="text-3xl font-extrabold text-emeraldAccent">
            {hasTrainedModel ? `${(model.accuracy * 100).toFixed(1)}%` : 'N/A'}
          </div>
          {hasTrainedModel ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-gray-400">
              <span>Precision <b className="text-white">{(model.precision * 100).toFixed(1)}%</b></span>
              <span>Recall <b className="text-white">{(model.recall * 100).toFixed(1)}%</b></span>
              <span>F1 <b className="text-white">{(model.f1_score * 100).toFixed(1)}%</b></span>
              <span>ROC-AUC <b className="text-white">{model.roc_auc?.toFixed(3) ?? 'N/A'}</b></span>
            </div>
          ) : (
            <p className="text-[11px] text-gray-400">No trained ModelVersion on record</p>
          )}
        </div>
        <div className="glass-card p-5 space-y-1">
          <div className="text-xs font-semibold text-gray-400">Synthetic Lenders</div>
          <div className="text-3xl font-extrabold text-cyanAccent">{metrics?.system_metrics?.total_lenders ?? 'N/A'}</div>
          <p className="text-[11px] text-gray-400">Demo lender accounts</p>
        </div>
        <div className="glass-card p-5 space-y-1">
          <div className="text-xs font-semibold text-gray-400">Quantum Runs Executed</div>
          <div className="text-3xl font-extrabold text-accent">{metrics?.system_metrics?.total_quantum_runs ?? 'N/A'}</div>
          <p className="text-[11px] text-gray-400">Qiskit QAOA Simulator</p>
        </div>
      </div>

      {hasTrainedModel && (
        <div className="glass-card p-4 text-xs text-gray-400">
          <div className="font-bold text-white mb-1">
            Model: {model.model_name} · {model.version}
          </div>
          <div>
            Evaluation dataset: {model.training_dataset_size ?? 'N/A'} rows ·
            Training data type: <span className="text-warning">{model.training_data_type || 'SYNTHETIC'}</span>.
          </div>
          <div className="mt-1">
            Synthetic demonstration metrics only; this model has not been validated
            against real hawker repayment outcomes.
          </div>
        </div>
      )}

      {/* Audit Logs Table */}
      <div className="glass-card p-6 space-y-4">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" /> Immutable Audit Log Trail
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-surfaceLight/80 text-gray-200 uppercase font-bold border-b border-border">
              <tr>
                <th className="p-3">Timestamp</th>
                <th className="p-3">Action</th>
                <th className="p-3">Resource Type</th>
                <th className="p-3">Resource ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60 font-mono">
              {auditLogs.slice(0, 8).map((log) => (
                <tr key={log.id}>
                  <td className="p-3 text-gray-400">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="p-3 font-bold text-cyanAccent">{log.action}</td>
                  <td className="p-3">{log.resource_type}</td>
                  <td className="p-3 text-gray-400 truncate max-w-xs">{log.resource_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
