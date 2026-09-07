'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { LogIn, UserPlus } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = mode === 'login'
        ? await login(email, password)
        : await register(email, password, 'VENDOR');

      if (user.role === 'VENDOR') router.push('/vendor/dashboard');
      else if (user.role === 'LENDER') router.push('/lender/dashboard');
      else router.push('/admin/dashboard');
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-12 space-y-6">
      <div className="brutal-card p-6 space-y-4">
        <h1 className="font-mono font-black text-xl uppercase tracking-tight flex items-center gap-2">
          {mode === 'login' ? <LogIn className="w-5 h-5 text-brandRed" /> : <UserPlus className="w-5 h-5 text-brandRed" />}
          {mode === 'login' ? 'Sign In' : 'Create Vendor Account'}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono font-bold uppercase mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border-2 border-black dark:border-white bg-transparent px-3 py-2 font-mono text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-mono font-bold uppercase mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border-2 border-black dark:border-white bg-transparent px-3 py-2 font-mono text-sm"
            />
          </div>

          {mode === 'register' && (
            <p className="text-[11px] font-mono text-gray-500">Self-registration is for hawker vendors. Lender and admin accounts are issued internally.</p>
          )}

          {error && <p className="text-brandRed text-xs font-mono font-bold">{error}</p>}

          <button type="submit" disabled={loading} className="brutal-btn w-full px-4 py-2 bg-brandRed text-white text-sm">
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <button
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          className="text-xs font-mono underline w-full text-center"
        >
          {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign in'}
        </button>
      </div>
    </div>
  );
}
