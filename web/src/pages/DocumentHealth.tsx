import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { VaultDocument } from '../types';
import { LoadingState, ErrorState } from '../components/common/UIStates';
import {
  ChevronLeft,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Bell,
  ChevronDown,
  ChevronUp,
  MapPin,
  ExternalLink,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

export const DocumentHealth: React.FC = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [reminders, setReminders] = useState<Record<string, boolean>>({
    doc_03: true,
    doc_02: true,
  });

  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err?.message || 'Failed to load document health.');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (docId: string) => {
    setExpandedSteps((prev) => ({ ...prev, [docId]: !prev[docId] }));
  };

  const toggleReminder = (docId: string) => {
    setReminders((prev) => ({ ...prev, [docId]: !prev[docId] }));
  };

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'दस्तावेज़ स्वास्थ्य स्कोर की गणना हो रही है...' : 'Auditing validity cycles and computing expiration risks...'} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadDocs} />;
  }

  // Calculate health metrics
  const total = documents.length;
  const validCount = documents.filter((d) => d.status === 'VALID').length;
  const expiringCount = documents.filter((d) => d.status === 'EXPIRING_SOON').length;
  const expiredCount = documents.filter((d) => d.status === 'EXPIRED').length;
  const healthPercent = total > 0 ? Math.round((validCount / total) * 100) : 100;

  // Sort by urgency: EXPIRED first, then EXPIRING_SOON, then VALID
  const sortedDocs = [...documents].sort((a, b) => {
    const priority = { EXPIRED: 1, EXPIRING_SOON: 2, VALID: 3 };
    return priority[a.status] - priority[b.status];
  });

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/documents"
          className="text-xs sm:text-sm font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 transition"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>{language === 'hi' ? 'दस्तावेज़ वॉल्ट पर वापस जाएं' : 'Back to Document Vault'}</span>
        </Link>
      </div>

      {/* Top Health Summary Card with Circular Ring */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-xs">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center sm:text-left">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              {language === 'hi' ? 'दस्तावेज़ स्वास्थ्य व नवीनीकरण स्थिति' : 'Document Health & Expiry Readiness'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 max-w-md">
              {language === 'hi'
                ? 'समय पर नवीनीकरण न होने पर छात्रवृत्ति अथवा सब्सिडी खारिज हो सकती है।'
                : 'Government schemes instantly reject expired certificates. Maintain 100% validity.'}
            </p>
          </div>

          {/* Health Ring Visualizer */}
          <div className="flex items-center gap-6">
            <div className="relative w-28 h-28 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  stroke="#F1F5F9"
                  strokeWidth="10"
                  fill="transparent"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  stroke={healthPercent > 70 ? '#138808' : '#E8710A'}
                  strokeWidth="10"
                  strokeDasharray={251.2}
                  strokeDashoffset={251.2 - (251.2 * healthPercent) / 100}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-2xl font-extrabold text-slate-900">{healthPercent}%</span>
                <span className="text-[10px] font-bold uppercase text-slate-500">
                  {language === 'hi' ? 'वैध' : 'Valid'}
                </span>
              </div>
            </div>

            {/* Counts Breakdown */}
            <div className="space-y-2 text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-slate-600">{language === 'hi' ? 'समाप्त:' : 'Expired:'}</span>
                <span className="font-bold text-slate-900">{expiredCount}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-slate-600">{language === 'hi' ? '30 दिन में समाप्त:' : 'Expiring in 30d:'}</span>
                <span className="font-bold text-slate-900">{expiringCount}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-gov-green" />
                <span className="text-slate-600">{language === 'hi' ? 'पूर्ण वैध:' : 'Valid:'}</span>
                <span className="font-bold text-slate-900">{validCount}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mandatory Regulatory Note */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex items-center gap-3 text-xs text-slate-600">
        <ShieldAlert className="w-5 h-5 text-saffron-600 shrink-0" />
        <p className="font-medium">
          <strong>{language === 'hi' ? 'महत्वपूर्ण सूचना:' : 'Notice:'}</strong> {language === 'hi' ? 'हम समय-सीमा व वैधता समाप्त होने की पहचान करते हैं, लेकिन नवीनीकरण आवेदन आपको संबंधित सरकारी पोर्टल या तहसील में स्वयं करना होगा।' : 'We detect expiry and guide the renewal steps, but you must renew the document yourself with the issuing revenue authority.'}
        </p>
      </div>

      {/* Urgency-Sorted Document Health List */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900">
          {language === 'hi' ? 'नवीनीकरण प्राथमिकता सूची' : 'Urgency Sorted Renewal List'}
        </h2>

        <div className="space-y-3">
          {sortedDocs.map((doc) => {
            const isExpired = doc.status === 'EXPIRED';
            const isExpiring = doc.status === 'EXPIRING_SOON';
            const isExpanded = !!expandedSteps[doc.id];
            const hasReminder = !!reminders[doc.id];

            return (
              <div
                key={doc.id}
                className={`bg-white rounded-2xl border transition-all p-5 shadow-xs ${
                  isExpired
                    ? 'border-red-200 ring-1 ring-red-500/20'
                    : isExpiring
                    ? 'border-amber-200 ring-1 ring-amber-500/20'
                    : 'border-slate-200'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-slate-900 text-base">
                        {doc.doc_type}
                      </h3>

                      <span
                        className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                          isExpired
                            ? 'bg-red-100 text-red-700'
                            : isExpiring
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-green-100 text-gov-green'
                        }`}
                      >
                        {isExpired
                          ? (language === 'hi' ? 'समय समाप्त (Expired)' : 'Expired')
                          : isExpiring
                          ? (language === 'hi' ? '28 दिन शेष' : '28 days left')
                          : (language === 'hi' ? 'वैध (Valid)' : 'Valid')}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                      <span>{language === 'hi' ? 'अंतिम तिथि:' : 'Valid until:'} <strong>{doc.expiry_date}</strong></span>
                      {doc.linked_scheme_ids.length > 0 && (
                        <span className="font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                          {language === 'hi' ? `रोक रहा है: ${doc.linked_scheme_ids.length} योजनाएं` : `Blocks ${doc.linked_scheme_ids.length} active applications`}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions: Remind Me toggle & Expand */}
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => toggleReminder(doc.id)}
                      className={`text-xs font-semibold px-3 py-1.5 rounded-xl border flex items-center gap-1.5 transition ${
                        hasReminder
                          ? 'bg-orange-50 text-saffron-700 border-saffron-300'
                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      <Bell className={`w-3.5 h-3.5 ${hasReminder ? 'text-saffron-600 fill-saffron-600' : ''}`} />
                      <span>{hasReminder ? (language === 'hi' ? 'अलर्ट चालू' : 'Remind ON') : (language === 'hi' ? 'रिमाइंडर लगाएं' : 'Remind me')}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => toggleExpand(doc.id)}
                      className="text-xs font-bold text-saffron-600 hover:text-saffron-700 flex items-center gap-1 py-1.5 px-2.5 rounded-lg hover:bg-orange-50 transition"
                    >
                      <span>{language === 'hi' ? 'नवीनीकरण कैसे करें' : 'How to renew'}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* How to Renew Expandable */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-100 text-xs sm:text-sm space-y-3 bg-slate-50/50 p-3.5 rounded-xl">
                    <h4 className="font-bold text-slate-900">
                      {language === 'hi' ? 'चरण-दर-चरण नवीनीकरण प्रक्रिया:' : 'Step-by-Step Renewal Guide:'}
                    </h4>

                    <ol className="list-decimal pl-4 space-y-1.5 text-slate-700">
                      <li>
                        {language === 'hi'
                          ? 'सरल पोर्टल (saralharyana.gov.in) अथवा स्थानीय अंत्योदय सेवा केंद्र पर जाएं।'
                          : 'Visit state citizen service portal (e.g., saralharyana.gov.in / e-District) or nearest CSC center.'}
                      </li>
                      <li>
                        {language === 'hi'
                          ? 'आवेदन संख्या, पुराना प्रमाण पत्र और परिवार पहचान पत्र (PPP) साथ रखें।'
                          : 'Keep your previous certificate number, electricity bill, and Parivar Pehchan Patra ready.'}
                      </li>
                      <li>
                        {language === 'hi'
                          ? 'पटवारी और तहसीलदार से सत्यापन के पश्चात 7-10 कार्यदिवसों में डिजिटल प्रमाण पत्र डाउनलोड करें।'
                          : 'Revenue Tehsildar verification takes 7-10 working days. Download signed digitally.'}
                      </li>
                    </ol>

                    <div className="p-2.5 bg-white rounded-lg border border-slate-200 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-slate-700 font-semibold text-xs">
                        <MapPin className="w-4 h-4 text-saffron-600 shrink-0" />
                        <span>{language === 'hi' ? 'निकटतम तहसील कार्यालय: तहसील कॉम्पलेक्स, रोहतक' : 'Nearest Revenue Office: Tehsil Complex, Rohtak, Haryana'}</span>
                      </div>
                      <a
                        href="https://maps.google.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-bold text-saffron-600 hover:underline flex items-center gap-1"
                      >
                        <span>{language === 'hi' ? 'नक्शा देखें' : 'View Map'}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
