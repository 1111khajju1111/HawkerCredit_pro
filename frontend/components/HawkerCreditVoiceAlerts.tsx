'use client';

import { useCallback, useEffect, useState } from 'react';

type VoiceAlert = {
  id: string;
  label: string;
  text: string;
};

const ALERTS: VoiceAlert[] = [
  { id: 'transaction', label: 'Transaction received', text: 'HawkerCredit: Transaction received successfully.' },
  { id: 'ai', label: 'AI assessment complete', text: 'HawkerCredit: AI credit assessment completed. Repayment probability is eighty two percent.' },
  { id: 'qubo', label: 'QUBO formulated', text: 'HawkerCredit: Portfolio constraints have been converted into a QUBO optimization problem.' },
  { id: 'qaoa', label: 'QAOA complete', text: 'HawkerCredit: QAOA portfolio optimization completed. A recommended portfolio has been identified.' },
  { id: 'validation', label: 'Validation passed', text: 'HawkerCredit: Classical post validation passed. Capital, risk, and concentration constraints are satisfied.' },
  { id: 'decision', label: 'Human decision required', text: 'HawkerCredit: Recommendation ready. Final lending decision requires an authorized human underwriter.' },
];

export default function HawkerCreditVoiceAlerts() {
  const [enabled, setEnabled] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [rate, setRate] = useState(0.95);
  const [volume, setVolume] = useState(1);
  const [status, setStatus] = useState('Bluetooth speaker can be selected as the system audio output.');

  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load);
  }, []);

  const speak = useCallback((text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setStatus('Speech synthesis is not supported in this browser.');
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const preferred = voices.find(v => /en-IN/i.test(v.lang)) || voices.find(v => /en-US|en-GB/i.test(v.lang));
    if (preferred) utterance.voice = preferred;
    utterance.rate = rate;
    utterance.volume = volume;
    utterance.onstart = () => setStatus('Speaking through the current system audio output…');
    utterance.onend = () => setStatus('Ready.');
    utterance.onerror = () => setStatus('Speech failed. Check browser audio permissions and the Bluetooth connection.');
    window.speechSynthesis.speak(utterance);
  }, [rate, volume, voices]);

  const announce = (alert: VoiceAlert) => {
    if (!enabled) setEnabled(true);
    speak(alert.text);
  };

  return (
    <section style={{ border: '1px solid rgba(255,255,255,.12)', borderRadius: 18, padding: 20, background: 'rgba(20,25,35,.85)', color: '#fff', maxWidth: 760 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1.5, opacity: .65 }}>HARDWARE / VOICE INTERFACE</div>
          <h2 style={{ margin: '5px 0', fontSize: 22 }}>🔊 HawkerCredit Voice Alerts</h2>
          <div style={{ fontSize: 12, opacity: .7 }}>{status}</div>
        </div>
        <button
          onClick={() => setEnabled(v => !v)}
          style={{ padding: '9px 14px', borderRadius: 10, border: 0, cursor: 'pointer', fontWeight: 800, color: '#fff', background: enabled ? '#15803d' : '#374151' }}
        >
          {enabled ? 'VOICE ON' : 'VOICE OFF'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(210px,1fr))', gap: 10, marginTop: 18 }}>
        {ALERTS.map(alert => (
          <button
            key={alert.id}
            onClick={() => announce(alert)}
            style={{ textAlign: 'left', padding: 13, borderRadius: 12, border: '1px solid rgba(255,255,255,.10)', background: 'rgba(255,255,255,.05)', color: '#fff', cursor: 'pointer' }}
          >
            🔊 <strong>{alert.label}</strong>
            <div style={{ fontSize: 11, opacity: .55, marginTop: 5 }}>Play announcement</div>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 18, marginTop: 18, flexWrap: 'wrap', fontSize: 12 }}>
        <label>Volume {Math.round(volume * 100)}%
          <input style={{ display: 'block', width: 150 }} type="range" min="0" max="1" step="0.05" value={volume} onChange={e => setVolume(Number(e.target.value))} />
        </label>
        <label>Speed {rate.toFixed(2)}×
          <input style={{ display: 'block', width: 150 }} type="range" min="0.7" max="1.2" step="0.05" value={rate} onChange={e => setRate(Number(e.target.value))} />
        </label>
      </div>

      <p style={{ margin: '16px 0 0', fontSize: 11, opacity: .55 }}>
        Tip: connect the Bluetooth speaker to the laptop/phone first, then press a button. No Bluetooth SDK or backend changes are required.
      </p>
    </section>
  );
}
