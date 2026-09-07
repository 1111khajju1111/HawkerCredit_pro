const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1"

export async function fetchApi<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'API Error' }));
    throw new Error(errorData.detail || 'Network request failed');
  }

  return res.json();
}

export const api = {
  // Auth
  login: (email: string, pass: string) => fetchApi('/auth/login', { method: 'POST', body: JSON.stringify({ email, password: pass }) }),
  register: (email: string, pass: string, role: string, phone?: string) => fetchApi('/auth/register', { method: 'POST', body: JSON.stringify({ email, password: pass, role, phone }) }),

  // Vendor
  getVendors: () => fetchApi('/vendors'),
  getLenderSummary: () => fetchApi('/vendors/lender-summary'),
  getVendor: (id: string) => fetchApi(`/vendors/${id}`),

  // Transactions & Expenses
  getTransactions: (vendorId: string) => fetchApi(`/transactions/${vendorId}`),
  addTransaction: (vendorId: string, data: any) => fetchApi(`/transactions?vendor_id=${vendorId}`, { method: 'POST', body: JSON.stringify(data) }),
  getExpenses: (vendorId: string) => fetchApi(`/expenses/${vendorId}`),
  addExpense: (vendorId: string, data: any) => fetchApi(`/expenses?vendor_id=${vendorId}`, { method: 'POST', body: JSON.stringify(data) }),

  // AI & Credit Profile
  getCreditProfile: (vendorId: string) => fetchApi(`/credit-score/${vendorId}`),
  postVoiceTransaction: (transcript: string) => fetchApi('/ai/voice-transaction', { method: 'POST', body: JSON.stringify({ transcript }) }),
  postReceiptOCR: async (file: File) => {
    // Multipart upload -- deliberately bypasses fetchApi, which always sets
    // Content-Type: application/json. FormData needs the browser to set its
    // own multipart boundary, so Content-Type must be left unset here.
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/ai/receipt-ocr`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: formData,
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: 'Receipt upload failed' }));
      throw new Error(errorData.detail || 'Receipt upload failed');
    }
    return res.json();
  },
  getForecast: (vendorId: string) => fetchApi(`/ai/forecast/${vendorId}`),
  getAnomalyAnalysis: (vendorId: string) => fetchApi(`/ai/anomaly-detection/${vendorId}`),
  getAiCoach: (vendorId: string, query?: string) => fetchApi(`/ai/coach/${vendorId}${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  getDataQuality: (vendorId: string) => fetchApi(`/ai/data-quality/${vendorId}`),

  // Loans & Human Underwriting
  getLoans: () => fetchApi('/loans'),
  getVendorLoans: (vendorId: string) => fetchApi(`/loans/vendor/${vendorId}`),
  requestLoan: (vendorId: string, data: any) => fetchApi(`/loans?vendor_id=${vendorId}`, { method: 'POST', body: JSON.stringify(data) }),
  underwriteLoan: (loanId: string, decision: string, notes?: string) => fetchApi('/loans/underwrite', { method: 'POST', body: JSON.stringify({ loan_id: loanId, decision, notes }) }),

  // Quantum Optimization & Portfolio
  runQuantumOptimize: (capital: number = 1000000, riskTolerance: number = 0.25, pLayers: number = 2, shots: number = 1024) => 
    fetchApi('/quantum/optimize', { 
      method: 'POST', 
      body: JSON.stringify({ available_capital: capital, max_risk_tolerance: riskTolerance, p_layers: pLayers, shots }) 
    }),
  getQuantumBenchmark: (capital: number = 1000000) => fetchApi(`/quantum/benchmark?available_capital=${capital}`),
  getQuantumRun: (runId: string) => fetchApi(`/quantum/runs/${runId}`),
  getLatestQuantumRun: () => fetchApi('/quantum/runs/latest'),

  // Consent & Audit & Admin
  getConsent: (vendorId: string) => fetchApi(`/consent/${vendorId}`),
  toggleConsent: (consentId: string, granted: boolean) => fetchApi(`/consent/toggle?consent_id=${consentId}&granted=${granted}`, { method: 'POST' }),
  getAuditLogs: () => fetchApi('/audit-logs'),
  getAdminMetrics: () => fetchApi('/admin/metrics'),
};
