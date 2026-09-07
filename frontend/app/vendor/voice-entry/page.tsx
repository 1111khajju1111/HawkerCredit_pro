'use client';

import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { Mic, MicOff, CheckCircle, ArrowLeft, Languages } from 'lucide-react';
import Link from 'next/link';

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionEvent extends Event {
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionInstance;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const LANGUAGES = [
  {
    code: 'en-IN',
    label: 'ENGLISH',
  },
  {
    code: 'hi-IN',
    label: 'हिन्दी',
  },
  {
    code: 'te-IN',
    label: 'తెలుగు',
  },
];

export default function VoiceEntryPage() {
  const { user } = useRequireAuth(['VENDOR']);

  const [transcript, setTranscript] = useState(
    'Today I sold vegetables worth 4500 rupees and spent 1800 on stock.'
  );

  const [parsedData, setParsedData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [language, setLanguage] = useState('en-IN');
  const [isListening, setIsListening] = useState(false);
  const [micSupported, setMicSupported] = useState(true);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const baseTranscriptRef = useRef('');

  useEffect(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      setMicSupported(false);
      return;
    }

    const recognition = new SpeechRecognitionAPI();

    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalText = '';
      let interimText = '';

      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i];

        if (result.isFinal) {
          finalText += result[0].transcript + ' ';
        } else {
          interimText += result[0].transcript;
        }
      }

      const combined = [
        baseTranscriptRef.current,
        finalText.trim(),
        interimText.trim(),
      ]
        .filter(Boolean)
        .join(' ')
        .trim();

      setTranscript(combined);
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      console.error('Speech recognition error:', event.error);

      if (event.error === 'not-allowed') {
        setError(
          'Microphone permission was denied. Please allow microphone access in your browser.'
        );
      } else if (event.error === 'no-speech') {
        setError('No speech detected. Please speak clearly into the microphone.');
      } else if (event.error === 'audio-capture') {
        setError('No microphone was detected. Please check your microphone.');
      } else {
        setError(`Microphone error: ${event.error}`);
      }

      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [language]);

  const startListening = () => {
    if (!recognitionRef.current) {
      setError(
        'Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.'
      );
      return;
    }

    setError(null);

    baseTranscriptRef.current = transcript.trim();

    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error('Could not start microphone:', err);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    setIsListening(false);
  };

  const clearTranscript = () => {
    stopListening();
    setTranscript('');
    baseTranscriptRef.current = '';
    setParsedData(null);
    setSaved(false);
    setError(null);
  };

  const handleLanguageChange = (newLanguage: string) => {
    stopListening();
    setLanguage(newLanguage);
  };

  const handleProcessVoice = async () => {
    if (!transcript.trim()) {
      setError('Please speak something or enter a transaction manually.');
      return;
    }

    setLoading(true);
    setSaved(false);
    setError(null);

    try {
      const result = await api.postVoiceTransaction(transcript);
      setParsedData(result);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to process voice entry');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!parsedData || !user?.vendor_id) return;

    try {
      const vendorId = user.vendor_id;

      await api.addTransaction(vendorId, {
        amount: parsedData.sales,
        transaction_type: 'SALE',
        payment_method: 'CASH',
        source: 'VOICE',
        confidence_score: parsedData.confidence,
      });

      if (parsedData.expenses > 0) {
        await api.addExpense(vendorId, {
          category: parsedData.category || 'STOCK',
          amount: parsedData.expenses,
          description: 'Voice diary stock expense',
          source: 'VOICE',
        });
      }

      setSaved(true);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to save entry');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 font-mono">
      <Link
        href="/vendor/dashboard"
        className="text-xs font-black uppercase text-gray-500 hover:text-brandRed flex items-center gap-1"
      >
        <ArrowLeft className="w-4 h-4" />
        BACK TO DASHBOARD
      </Link>

      <div className="brutal-card p-6 space-y-6 border-l-8 border-l-brandRed">
        <div>
          <span className="brutal-badge bg-brandRed text-white">
            VOICE NLP AI
          </span>

          <h1 className="text-2xl font-black uppercase text-black dark:text-white mt-1 flex items-center gap-2">
            <Mic className="w-6 h-6 text-brandRed" />
            VOICE FINANCIAL ENTRY
          </h1>

          <p className="text-xs text-gray-500 font-semibold">
            Speak naturally in English, Hindi or Telugu. Your speech will be
            converted into a financial transaction.
          </p>
        </div>

        {/* LANGUAGE SELECTOR */}
        <div className="space-y-2">
          <label className="text-xs font-black uppercase text-black dark:text-white flex items-center gap-2">
            <Languages className="w-4 h-4 text-brandRed" />
            SPEECH LANGUAGE
          </label>

          <div className="grid grid-cols-3 gap-2">
            {LANGUAGES.map((item) => (
              <button
                key={item.code}
                type="button"
                onClick={() => handleLanguageChange(item.code)}
                className={`border-2 border-black dark:border-white py-2 px-2 text-xs font-black ${
                  language === item.code
                    ? 'bg-brandRed text-white'
                    : 'bg-white dark:bg-black text-black dark:text-white'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* MICROPHONE */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            disabled={!micSupported}
            className={`brutal-btn w-full py-4 text-xs flex items-center justify-center gap-2 ${
              isListening
                ? 'bg-black text-white dark:bg-white dark:text-black'
                : 'bg-brandRed text-white'
            } ${!micSupported ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isListening ? (
              <>
                <MicOff className="w-5 h-5" />
                STOP MICROPHONE
              </>
            ) : (
              <>
                <Mic className="w-5 h-5" />
                START MICROPHONE
              </>
            )}
          </button>

          {!micSupported && (
            <p className="text-xs font-bold text-brandRed">
              Microphone speech recognition is not supported in this browser.
              Please use Google Chrome or Microsoft Edge.
            </p>
          )}

          {isListening && (
            <div className="border-2 border-brandRed p-3 text-center text-xs font-black uppercase">
              🎙️ LISTENING... SPEAK YOUR SALES AND EXPENSES
            </div>
          )}
        </div>

        {/* TRANSCRIPT */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-black uppercase text-black dark:text-white">
              SPOKEN SPEECH TRANSCRIPT
            </label>

            <button
              type="button"
              onClick={clearTranscript}
              className="text-xs font-black uppercase text-brandRed"
            >
              CLEAR
            </button>
          </div>

          <textarea
            value={transcript}
            onChange={(e) => {
              setTranscript(e.target.value);
              baseTranscriptRef.current = e.target.value;
            }}
            className="w-full h-32 p-3 bg-lightSurface2 dark:bg-darkSurface2 border-2 border-black dark:border-white text-sm font-semibold text-black dark:text-white focus:outline-none focus:border-brandRed"
            placeholder={
              language === 'te-IN'
                ? 'ఉదాహరణ: ఈ రోజు కూరగాయలు అమ్మి 4500 రూపాయలు సంపాదించాను మరియు స్టాక్ కోసం 1800 ఖర్చు చేశాను.'
                : language === 'hi-IN'
                  ? 'उदाहरण: आज मैंने सब्जियां बेचकर 4500 रुपये कमाए और स्टॉक पर 1800 रुपये खर्च किए।'
                  : 'Example: Today I sold vegetables for 4500 rupees and spent 1800 on stock.'
            }
          />
        </div>

        <button
          type="button"
          onClick={handleProcessVoice}
          disabled={loading || !transcript.trim()}
          className="brutal-btn w-full py-3.5 bg-brandRed text-white text-xs"
        >
          {loading
            ? 'EXTRACTING FINANCIAL ENTITIES...'
            : 'PROCESS VOICE ENTRY (NLP AI)'}
        </button>

        {/* ERROR */}
        {error && (
          <div className="p-3 text-xs font-black text-center uppercase text-brandRed border-2 border-brandRed">
            {error}
          </div>
        )}

        {/* EXTRACTED DATA */}
        {parsedData && (
          <div className="brutal-card p-5 space-y-4 bg-lightSurface2 dark:bg-darkSurface2 border-l-4 border-l-brandRed">
            <div className="flex items-center justify-between border-b-2 border-black dark:border-white pb-3">
              <span className="text-xs font-black uppercase text-brandRed">
                AI EXTRACTED FINANCIAL RECORD
              </span>

              <span className="brutal-badge bg-black text-white dark:bg-white dark:text-black">
                CONFIDENCE: {(parsedData.confidence * 100).toFixed(0)}%
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-bold text-gray-500 uppercase">
                  EXTRACTED REVENUE
                </div>

                <div className="text-2xl font-black text-black dark:text-white">
                  ₹{parsedData.sales.toLocaleString()}
                </div>
              </div>

              <div>
                <div className="text-xs font-bold text-gray-500 uppercase">
                  EXTRACTED STOCK EXPENSE
                </div>

                <div className="text-2xl font-black text-brandRed">
                  ₹{parsedData.expenses.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="text-xs font-bold text-gray-500 uppercase">
              CATEGORY:{' '}
              <strong className="text-black dark:text-white">
                {parsedData.category}
              </strong>
            </div>

            {!saved ? (
              <button
                type="button"
                onClick={handleConfirmSave}
                className="brutal-btn w-full py-3 bg-black text-white dark:bg-white dark:text-black text-xs flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-4 h-4 text-brandRed" />
                CONFIRM & SAVE TO DATABASE
              </button>
            ) : (
              <div className="brutal-card-red p-3 text-xs font-black text-center flex items-center justify-center gap-2 uppercase">
                <CheckCircle className="w-4 h-4" />
                SUCCESSFULLY SAVED TO DATABASE!
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
