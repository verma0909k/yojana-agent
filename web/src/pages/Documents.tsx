import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { VaultDocument, ConsistencyIssue } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/common/UIStates';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Trash2,
  RefreshCw,
  Sparkles,
  Check,
  Shield,
  Activity,
  ArrowRight,
  ExternalLink,
  Edit2
} from 'lucide-react';

export const Documents: React.FC = () => {
  const { t, language } = useLanguage();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [consistencyIssues, setConsistencyIssues] = useState<ConsistencyIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Uploading state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedExtraction, setUploadedExtraction] = useState<{
    doc: VaultDocument;
    fields: Record<string, string>;
  } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [docs, issues] = await Promise.all([
        api.getDocuments(),
        api.getConsistencyIssues(),
      ]);
      setDocuments(docs);
      setConsistencyIssues(issues);
    } catch (err: any) {
      setError(err?.message || 'Failed to load documents vault.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const res = await api.uploadDocument(file);
      setUploadedExtraction({
        doc: res.document,
        fields: res.extractedFields as Record<string, string>,
      });
      // Refresh document list
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      alert('Upload failed: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (window.confirm(language === 'hi' ? 'क्या आप इस दस्तावेज़ को हटाना चाहते हैं?' : 'Are you sure you want to remove this document?')) {
      await api.deleteDocument(docId);
      setDocuments(documents.filter((d) => d.id !== docId));
    }
  };

  const handleConfirmExtraction = () => {
    setUploadedExtraction(null);
  };

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'वॉल्ट दस्तावेज़ लोड हो रहे हैं...' : 'Decrypting and loading documents from secure vault...'} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Health Link */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            {t('docs.title')}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {language === 'hi'
              ? 'एन्क्रिप्टेड डिजिटल लॉकर - सरकारी आवेदन हेतु प्रमाणित दस्तावेज़'
              : 'Zero-knowledge encrypted storage for certificates, identity & land records'}
          </p>
        </div>

        <Link
          to="/documents/health"
          className="min-h-[44px] px-4 py-2 bg-orange-50 hover:bg-orange-100 text-saffron-700 border border-saffron-200 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition"
        >
          <Activity className="w-4 h-4 text-saffron-600" />
          <span>{t('docs.health_link')}</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Consistency Issues Warning Banner */}
      {consistencyIssues.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-bold text-amber-900 text-sm sm:text-base">
                {t('docs.consistency_warn')} ({consistencyIssues.length})
              </h3>
              <div className="mt-2 space-y-2">
                {consistencyIssues.map((issue) => (
                  <div key={issue.id} className="text-xs sm:text-sm text-amber-800 bg-white/70 p-2.5 rounded-lg border border-amber-200/60">
                    <p className="font-semibold">{issue.message}</p>
                    <span className="text-[11px] text-amber-700 block mt-0.5">
                      {language === 'hi' ? 'प्रभावित दस्तावेज़:' : 'Impacted documents:'} {issue.documents.join(', ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Drag & Drop Upload Zone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="bg-white border-2 border-dashed border-saffron-300 hover:border-saffron-500 rounded-2xl p-8 text-center cursor-pointer transition bg-orange-50/20 hover:bg-orange-50/40"
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/*,.pdf"
          className="hidden"
        />
        <div className="w-14 h-14 bg-orange-100 text-saffron-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
          {isUploading ? (
            <RefreshCw className="w-7 h-7 animate-spin" />
          ) : (
            <UploadCloud className="w-7 h-7" />
          )}
        </div>
        <h3 className="font-bold text-slate-900 text-base mb-1">
          {isUploading
            ? (language === 'hi' ? 'एआई दस्तावेज़ पढ़ रहा है...' : 'AI Vision OCR Parsing Document...')
            : t('docs.upload_drag')}
        </h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          {language === 'hi'
            ? 'आधार कार्ड, आय प्रमाण पत्र, जाति प्रमाण पत्र, खतौनी या बैंक पासबुक (JPG, PNG, PDF)'
            : 'Supports Aadhaar, Income certificate, Caste certificate, Khasra, and Bank passbook'}
        </p>
      </div>

      {/* AI Extracted Panel (After Upload) */}
      {uploadedExtraction && (
        <div className="bg-white rounded-2xl p-5 border-2 border-gov-green shadow-md animate-fade-in space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-gov-green" />
              <h3 className="font-bold text-slate-900 text-base">
                {language === 'hi' ? 'एआई द्वारा निकाले गए विवरण (जांचें एवं पुष्टि करें)' : 'AI Extracted Metadata (Review & Confirm)'}
              </h3>
            </div>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-50 text-gov-green border border-green-200">
              96% OCR Confidence
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(uploadedExtraction.fields).map(([key, val]) => (
              <div key={key} className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-xs text-slate-500 font-semibold block">{key}</span>
                <input
                  type="text"
                  defaultValue={val}
                  className="w-full text-sm font-bold text-slate-900 bg-transparent border-b border-dashed border-slate-400 focus:outline-none focus:border-saffron-500 mt-0.5"
                />
              </div>
            ))}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleConfirmExtraction}
              className="px-5 py-2.5 bg-gov-green hover:bg-green-700 text-white font-bold rounded-xl text-sm shadow-sm flex items-center gap-2 transition"
            >
              <Check className="w-4 h-4" />
              <span>{language === 'hi' ? 'विवरण की पुष्टि करें और वॉल्ट में सहेजें' : 'Confirm & Save in Vault'}</span>
            </button>
          </div>
        </div>
      )}

      {/* Document Grid */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">
          {language === 'hi' ? 'सुरक्षित वॉल्ट में मौजूद दस्तावेज़' : 'Documents Stored in Vault'} ({documents.length})
        </h2>

        {documents.length === 0 ? (
          <EmptyState
            title={language === 'hi' ? 'कोई दस्तावेज़ नहीं मिला' : 'Vault is empty'}
            description={language === 'hi' ? 'योजनाओं के त्वरित आवेदन के लिए अपना पहला दस्तावेज़ अपलोड करें।' : 'Upload your identity or income certificates above to get started.'}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map((doc) => {
              const isValid = doc.status === 'VALID';
              const isExpiring = doc.status === 'EXPIRING_SOON';
              const isExpired = doc.status === 'EXPIRED';

              return (
                <div
                  key={doc.id}
                  className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition p-5 flex flex-col justify-between"
                >
                  <div>
                    {/* Top: Thumbnail & Status */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="w-12 h-12 rounded-xl bg-orange-50 border border-saffron-100 flex items-center justify-center text-saffron-600 shrink-0 font-bold">
                        <FileText className="w-6 h-6" />
                      </div>

                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
                          isValid
                            ? 'bg-green-50 text-gov-green border border-green-200'
                            : isExpiring
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-red-50 text-red-700 border border-red-200'
                        }`}
                      >
                        {isValid ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
                        <span>{doc.status.replace('_', ' ')}</span>
                      </span>
                    </div>

                    <h3 className="font-bold text-slate-900 text-base leading-tight">
                      {doc.doc_type}
                    </h3>
                    <p className="text-xs text-slate-600 mt-1">
                      {language === 'hi' ? 'धारक:' : 'Holder:'} <span className="font-semibold text-slate-800">{doc.holder_name}</span>
                    </p>

                    {/* Dates */}
                    <div className="mt-3 p-2.5 bg-slate-50 rounded-xl border border-slate-100 text-xs space-y-1">
                      <div className="flex justify-between text-slate-600">
                        <span>{language === 'hi' ? 'जारी तिथि:' : 'Issued:'}</span>
                        <span className="font-medium">{doc.issue_date}</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>{language === 'hi' ? 'वैधता समाप्त:' : 'Expires:'}</span>
                        <span className={`font-bold ${isExpired ? 'text-red-600' : isExpiring ? 'text-amber-600' : 'text-slate-800'}`}>
                          {doc.expiry_date}
                        </span>
                      </div>
                    </div>

                    {/* Linked schemes */}
                    <div className="mt-3">
                      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                        {language === 'hi' ? 'उपयोग होने वाली योजनाएं:' : 'Linked Schemes:'}
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {doc.linked_scheme_ids.map((sId) => (
                          <span key={sId} className="px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-700 font-medium">
                            {sId}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Actions: Replace & Delete */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 mt-4">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-xs font-semibold text-slate-600 hover:text-saffron-600 flex items-center gap-1.5 py-1.5 px-2 rounded-lg hover:bg-slate-50 transition"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>{language === 'hi' ? 'बदलें' : 'Replace'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="text-xs font-semibold text-red-600 hover:text-red-700 flex items-center gap-1.5 py-1.5 px-2 rounded-lg hover:bg-red-50 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>{language === 'hi' ? 'हटाएं' : 'Delete'}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
