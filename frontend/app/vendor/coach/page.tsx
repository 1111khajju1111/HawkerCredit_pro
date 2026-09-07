'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { ShieldCheck, ArrowLeft, Send, Sparkles } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'coach';
  text: string;
}

export default function AiCoachPage() {
  const { user, loading: authLoading } = useRequireAuth(['VENDOR']);
  const [vendorId, setVendorId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (authLoading || !user?.vendor_id) return;
    setVendorId(user.vendor_id);

    async function loadInitialAdvice(vId: string) {
      setLoading(true);
      try {
        const advice = await api.getAiCoach(vId);
        setMessages([{ role: 'coach', text: advice.coach_response || JSON.stringify(advice) }]);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadInitialAdvice(user.vendor_id);
  }, [authLoading, user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleAsk() {
    if (!query.trim() || !vendorId) return;
    const userMsg = query.trim();
    setMessages((prev) => [...prev, { role: 'user', text: userMsg }]);
    setQuery('');
    setLoading(true);
    try {
      const advice = await api.getAiCoach(vendorId, userMsg);
      setMessages((prev) => [...prev, { role: 'coach', text: advice.coach_response || JSON.stringify(advice) }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { role: 'coach', text: `Error: ${err.message || 'could not reach coach'}` }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 font-mono">
      <Link href="/vendor/dashboard" className="text-xs font-black uppercase text-gray-500 hover:text-brandRed flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> BACK TO DASHBOARD
      </Link>

      <div className="brutal-card p-6 space-y-4 border-l-8 border-l-brandRed">
        <div>
          <span className="brutal-badge bg-brandRed text-white">AI FINANCIAL COACH</span>
          <h1 className="text-2xl font-black uppercase text-black dark:text-white mt-1 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-brandRed" /> ASK YOUR AI COACH
          </h1>
          <p className="text-xs text-gray-500 font-semibold">Personalized tips based on your credit profile and daily business data</p>
        </div>

        <div className="space-y-3 max-h-96 overflow-y-auto p-3 bg-lightSurface2 dark:bg-darkSurface2 border border-black dark:border-white">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`p-3 text-xs font-semibold border ${
                m.role === 'user'
                  ? 'bg-black text-white dark:bg-white dark:text-black border-black dark:border-white ml-8'
                  : 'bg-white dark:bg-darkSurface text-black dark:text-white border-brandRed mr-8'
              }`}
            >
              <div className="text-[10px] font-black uppercase mb-1 opacity-60">{m.role === 'user' ? 'YOU' : 'AI COACH'}</div>
              {m.text}
            </div>
          ))}
          {loading && <div className="text-xs font-bold text-gray-500 uppercase">THINKING...</div>}
          <div ref={bottomRef} />
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder="Ask about savings, loan amounts, expenses..."
            className="flex-1 p-3 bg-lightSurface2 dark:bg-darkSurface2 border-2 border-black dark:border-white text-sm font-semibold text-black dark:text-white focus:outline-none focus:border-brandRed"
          />
          <button
            onClick={handleAsk}
            disabled={loading || !query.trim()}
            className="brutal-btn px-4 bg-brandRed text-white text-xs flex items-center gap-1.5 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
