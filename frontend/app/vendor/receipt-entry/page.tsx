'use client';

import { useState, useRef } from 'react';
import { api } from '@/lib/api';
import { useRequireAuth } from '@/lib/auth';
import { Receipt, CheckCircle, ArrowLeft, Upload, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export default function ReceiptEntryPage() {
  const { user } = useRequireAuth(['VENDOR']);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setParsedData(null);
    setSaved(false);
    setError(null);
  };

  const handleProcessReceipt = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.postReceiptOCR(selectedFile);
      setParsedData(result);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to process receipt');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmSave = async () => {
    if (!parsedData || !user?.vendor_id) return;
    try {
      await api.addExpense(user.vendor_id, {
        category: parsedData.category || 'STOCK',
        amount: parsedData.amount,
        description: `${parsedData.merchant} (receipt scan)`,
        source: 'OCR',
      });
      setSaved(true);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to save entry');
    }
  };

  const isRealOcr = parsedData?.extraction_method === 'TESSERACT_OCR';

  return (
    <div className="max-w-2xl mx-auto space-y-6 font-mono">
      <Link href="/vendor/dashboard" className="text-xs font-black uppercase text-gray-500 hover:text-brandRed flex items-center gap-1">
        <ArrowLeft className="w-4 h-4" /> BACK TO DASHBOARD
      </Link>

      <div className="brutal-card p-6 space-y-6 border-l-8 border-l-brandRed">
        <div>
          <span className="brutal-badge bg-brandRed text-white">RECEIPT OCR</span>
          <h1 className="text-2xl font-black uppercase text-black dark:text-white mt-1 flex items-center gap-2">
            <Receipt className="w-6 h-6 text-brandRed" /> RECEIPT UPLOAD & CONFIRM
          </h1>
          <p className="text-xs text-gray-500 font-semibold">
            Upload a photo of a wholesale receipt or invoice. Nothing is saved until you confirm the extracted amount below.
          </p>
        </div>

        <div className="space-y-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full border-2 border-dashed border-black dark:border-white p-6 flex flex-col items-center gap-2 text-xs font-black uppercase text-gray-500 hover:border-brandRed hover:text-brandRed"
          >
            <Upload className="w-6 h-6" />
            {selectedFile ? selectedFile.name : 'TAP TO SELECT A RECEIPT PHOTO'}
          </button>
          {previewUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt="Receipt preview" className="w-full max-h-64 object-contain border-2 border-black dark:border-white" />
          )}
        </div>

        <button
          onClick={handleProcessReceipt}
          disabled={loading || !selectedFile}
          className="brutal-btn w-full py-3.5 bg-brandRed text-white text-xs disabled:opacity-50"
        >
          {loading ? 'READING RECEIPT...' : 'PROCESS RECEIPT (OCR)'}
        </button>

        {parsedData && (
          <div className="brutal-card p-5 space-y-4 bg-lightSurface2 dark:bg-darkSurface2 border-l-4 border-l-brandRed">
            <div className="flex items-center justify-between border-b-2 border-black dark:border-white pb-3">
              <span className="text-xs font-black uppercase text-brandRed">EXTRACTED RECEIPT DATA</span>
              <span className="brutal-badge bg-black text-white dark:bg-white dark:text-black">
                CONFIDENCE: {(parsedData.confidence * 100).toFixed(0)}%
              </span>
            </div>

            {/* Honesty label: real OCR vs. deterministic demo fallback -- never
                blurred together, so nobody mistakes a filename-keyed demo
                reading for a genuine extraction. */}
            <div className={`text-[10px] font-black uppercase flex items-center gap-1.5 ${isRealOcr ? 'text-green-600' : 'text-amber-600'}`}>
              {isRealOcr ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
              {isRealOcr ? 'Real OCR text extraction (Tesseract)' : 'Deterministic demo fallback (no OCR engine detected / low-confidence read)'}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-bold text-gray-500 uppercase">MERCHANT</div>
                <div className="text-lg font-black text-black dark:text-white">{parsedData.merchant}</div>
              </div>
              <div>
                <div className="text-xs font-bold text-gray-500 uppercase">AMOUNT</div>
                <div className="text-2xl font-black text-brandRed">₹{parsedData.amount.toLocaleString()}</div>
              </div>
            </div>

            <div className="text-xs font-bold text-gray-500 uppercase">
              CATEGORY: <strong className="text-black dark:text-white">{parsedData.category}</strong>
            </div>

            {!saved ? (
              <button
                onClick={handleConfirmSave}
                className="brutal-btn w-full py-3 bg-black text-white dark:bg-white dark:text-black text-xs flex items-center justify-center gap-2"
              >
                <CheckCircle className="w-4 h-4 text-brandRed" /> CONFIRM & SAVE TO LEDGER
              </button>
            ) : (
              <div className="brutal-card-red p-3 text-xs font-black text-center flex items-center justify-center gap-2 uppercase">
                <CheckCircle className="w-4 h-4" /> SAVED TO LEDGER
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="p-3 text-xs font-black text-center uppercase text-brandRed border-2 border-brandRed">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
