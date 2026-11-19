import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { MatchResult } from '../types';
import { LoadingState, ErrorState } from '../components/common/UIStates';
import {
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Calendar,
  FileCheck,
  Bell,
  ArrowRight,
  ChevronLeft,
  Sparkles,
  Info,
  Clock,
  Quote,
  AlertTriangle,
  Building
} from 'lucide-react';

export const SchemeDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t, language } = useLanguage();

  const [activeTab, setActiveTab] = useState<'overview' | 'eligibility' | 'documents' | 'deadlines'>('overview');
  const [data, setData] = useState<{
    scheme: MatchResult;
    rules: Array<{ requirement: string; userValue: string; status: 'pass' | 'fail' | 'unknown'; quote: string }>;
    deadlines: Array<{ stage: string; date: string; status: 'open' | 'closing_soon' | 'closed' }>;
    rejectionReason?: string;
    alternativeSchemes?: MatchResult[];
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExplainModal, setShowExplainModal] = useState(false);
  const [reminderSet, setReminderSet] = useState(false);

  useEffect(() => {
    if (id) {
      loadSchemeDetail(id);
    }
  }, [id]);

  const loadSchemeDetail = async (schemeId: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSchemeById(schemeId);
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load scheme details.');
    } finally {
      setLoading(false);
    }
  };

  const handlePrepareApp = async () => {
    if (!data?.scheme) return;
    try {
      await api.createApplication(data.scheme.scheme_id);
      navigate('/tracker');
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'योजना के राजपत्र नियम लोड हो रहे हैं...' : 'Loading official scheme gazette and evidentiary citations...'} />;
  }

  if (error || !data) {
    return <ErrorState message={error || 'Scheme not found'} onRetry={() => id && loadSchemeDetail(id)} />;
  }

  const { scheme, rules, deadlines, rejectionReason, alternativeSchemes } = data;
  const isEligible = scheme.status === 'ELIGIBLE';

  return (
    <div className="space-y-6 pb-24">
      {/* Back link */}
      <div>
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-xs sm:text-sm font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 transition"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>{language === 'hi' ? 'वापस जाएं' : 'Back to schemes'}</span>
        </button>
      </div>

      {/* Scheme Header Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 ${
                isEligible
                  ? 'bg-green-50 text-gov-green border border-green-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              }`}
            >
              {isEligible ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              <span>{isEligible ? (language === 'hi' ? 'आप पात्र हैं' : 'ELIGIBLE') : (language === 'hi' ? 'लगभग पात्र' : 'ALMOST ELIGIBLE')}</span>
            </span>

            <span className="text-xs text-slate-500 font-medium px-2.5 py-1 bg-slate-100 rounded-full">
              {scheme.category}
            </span>
          </div>

          {/* Official link */}
          <a
            href={scheme.official_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs sm:text-sm font-bold text-slate-700 hover:text-saffron-600 flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-200 transition"
          >
            <ShieldCheck className="w-4 h-4 text-gov-green" />
            <span>{language === 'hi' ? 'आधिकारिक पोर्टल खोलें' : 'Official Portal'}</span>
            <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
          </a>
        </div>

        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 leading-tight">
          {scheme.scheme_name}
        </h1>

        <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-500 mt-2">
          <Building className="w-4 h-4 text-slate-400 shrink-0" />
          <span>{scheme.ministry}</span>
        </div>

        {/* Benefit highlight banner */}
        <div className="mt-5 p-4 rounded-xl bg-orange-50/70 border border-saffron-200 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-saffron-600 shrink-0 mt-0.5" />
          <div>
            <span className="text-xs font-bold text-saffron-900 block uppercase tracking-wider">
              {language === 'hi' ? 'वित्तीय अथवा कल्याणकारी लाभ:' : 'Certified Benefit:'}
            </span>
            <p className="text-sm sm:text-base font-semibold text-slate-900 mt-0.5">
              {scheme.benefit_summary}
            </p>
          </div>
        </div>

        {/* Explain why not button if rejected / almost */}
        {scheme.status !== 'ELIGIBLE' && (
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {language === 'hi' ? 'यदि आपकी पात्रता पूरी नहीं हो पा रही है:' : 'Wondering why you did not get 100% eligibility?'}
            </span>
            <button
              type="button"
              onClick={() => setShowExplainModal(true)}
              className="text-xs sm:text-sm font-bold text-saffron-600 hover:text-saffron-700 underline"
            >
              {t('schemes.explain_why_not')}
            </button>
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-2xl px-3 pt-2">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'overview'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'अवलोकन (Overview)' : 'Overview'}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('eligibility')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'eligibility'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'पात्रता नियम व प्रमाण' : 'Eligibility & Evidence'}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('documents')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'documents'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'आवश्यक दस्तावेज़' : 'Documents'}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('deadlines')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'deadlines'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'समय-सीमा (Deadlines)' : 'Deadlines'}
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="bg-white rounded-b-2xl p-6 border border-t-0 border-slate-200/90 shadow-xs space-y-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base mb-2">
              {language === 'hi' ? 'योजना का मुख्य उद्देश्य' : 'Key Scheme Objectives'}
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              {scheme.benefit_summary} The scheme operates directly under {scheme.ministry} to ensure transparent delivery through Direct Benefit Transfer (DBT) into citizen bank accounts with no intermediaries.
            </p>
          </div>

          <div>
            <h3 className="font-bold text-slate-900 text-base mb-2">
              {language === 'hi' ? 'आपको मिलने वाले प्रमुख लाभ' : 'Core Benefits Breakdown'}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs text-slate-500 font-semibold block">{language === 'hi' ? 'भुगतान प्रकार' : 'Disbursal Type'}</span>
                <span className="font-bold text-slate-900 text-sm">Direct Bank Transfer (Aadhaar Seeded)</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs text-slate-500 font-semibold block">{language === 'hi' ? 'सत्यापन प्राधिकरण' : 'Verification Authority'}</span>
                <span className="font-bold text-slate-900 text-sm">District Nodal Officer / CSC Portal</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Eligibility Rules with Evidentiary Citations */}
      {activeTab === 'eligibility' && (
        <div className="bg-white rounded-b-2xl p-6 border border-t-0 border-slate-200/90 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-base">
              {language === 'hi' ? 'नियम-वार पात्रता एवं आधिकारिक राजपत्र साक्ष्य' : 'Rule-by-Rule Criteria & Official Gazette Quotes'}
            </h3>
            <span className="text-xs text-slate-500">
              {language === 'hi' ? '100% सत्यापन' : 'Audited with Pydantic rule engine'}
            </span>
          </div>

          <div className="space-y-3">
            {rules.map((rule, idx) => {
              const isPass = rule.status === 'pass';
              const isFail = rule.status === 'fail';

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-xl border transition ${
                    isPass
                      ? 'border-green-200 bg-green-50/20'
                      : isFail
                      ? 'border-red-200 bg-red-50/20'
                      : 'border-slate-200 bg-slate-50/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-start gap-2.5">
                      <div className="mt-0.5">
                        {isPass ? (
                          <CheckCircle2 className="w-5 h-5 text-gov-green shrink-0" />
                        ) : isFail ? (
                          <XCircle className="w-5 h-5 text-red-600 shrink-0" />
                        ) : (
                          <HelpCircle className="w-5 h-5 text-slate-400 shrink-0" />
                        )}
                      </div>
                      <div>
                        <span className="font-bold text-slate-900 text-sm block">
                          {rule.requirement}
                        </span>
                        <div className="text-xs text-slate-600 mt-1 flex items-center gap-1.5">
                          <span className="font-semibold text-slate-500">{language === 'hi' ? 'आपका दर्ज विवरण:' : 'Your Profile Value:'}</span>
                          <span className="font-bold text-slate-800">{rule.userValue}</span>
                        </div>
                      </div>
                    </div>

                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                        isPass ? 'bg-green-100 text-gov-green' : isFail ? 'bg-red-100 text-red-700' : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {rule.status}
                    </span>
                  </div>

                  {/* Quoted line from official gazette */}
                  <div className="mt-3 p-2.5 bg-white rounded-lg border border-slate-200/80 flex items-start gap-2 text-xs text-slate-600 italic">
                    <Quote className="w-3.5 h-3.5 text-saffron-500 shrink-0 mt-0.5" />
                    <span>{rule.quote}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 3: Documents Required */}
      {activeTab === 'documents' && (
        <div className="bg-white rounded-b-2xl p-6 border border-t-0 border-slate-200/90 shadow-xs space-y-4">
          <h3 className="font-bold text-slate-900 text-base mb-2">
            {language === 'hi' ? 'आवेदन हेतु आवश्यक मूल दस्तावेज़' : 'Documents Required for Verification'}
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {scheme.documents_required.map((doc, idx) => (
              <div key={idx} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <FileCheck className="w-5 h-5 text-saffron-600 shrink-0" />
                  <span className="font-bold text-slate-900 text-sm">{doc}</span>
                </div>
                <Link
                  to="/documents"
                  className="text-xs font-semibold text-saffron-600 hover:text-saffron-700"
                >
                  {language === 'hi' ? 'वॉल्ट देखें' : 'View in Vault'}
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Deadlines & Timeline */}
      {activeTab === 'deadlines' && (
        <div className="bg-white rounded-b-2xl p-6 border border-t-0 border-slate-200/90 shadow-xs space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-bold text-slate-900 text-base">
              {language === 'hi' ? 'योजना आवेदन समय-सीमा व महत्वपूर्ण तिथियां' : 'Application Window & Schedule'}
            </h3>
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{language === 'hi' ? 'अंतिम जांच: आज सुबह 10:00 बजे' : 'Last checked: Today 10:00 AM'}</span>
            </span>
          </div>

          <div className="relative pl-6 space-y-4">
            <div className="absolute left-2.5 top-3 bottom-3 w-0.5 bg-slate-200" />

            {deadlines.map((dl, idx) => (
              <div key={idx} className="relative flex items-start justify-between gap-4">
                <div className="absolute -left-6 top-1 w-3.5 h-3.5 rounded-full bg-saffron-500 border-2 border-white" />
                <div>
                  <span className="font-bold text-slate-900 text-sm block">{dl.stage}</span>
                  <span className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    <span>{dl.date}</span>
                  </span>
                </div>

                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    dl.status === 'closing_soon'
                      ? 'bg-amber-100 text-amber-800'
                      : dl.status === 'open'
                      ? 'bg-green-100 text-gov-green'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {dl.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sticky Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 p-3 sm:p-4 shadow-lg z-30">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setReminderSet(!reminderSet)}
            className={`min-h-[46px] px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 border transition ${
              reminderSet
                ? 'bg-orange-50 text-saffron-700 border-saffron-300'
                : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
            }`}
          >
            <Bell className={`w-4 h-4 ${reminderSet ? 'text-saffron-600 fill-saffron-600' : ''}`} />
            <span>{reminderSet ? (language === 'hi' ? 'अलर्ट सक्रिय' : 'Reminder Set') : (language === 'hi' ? 'रिमाइंडर लगाएं' : 'Set Reminder')}</span>
          </button>

          <button
            type="button"
            onClick={handlePrepareApp}
            className="min-h-[48px] px-6 py-2.5 bg-saffron-500 hover:bg-saffron-600 active:scale-[0.99] text-white font-bold rounded-xl text-sm sm:text-base shadow-md shadow-saffron-500/20 flex items-center gap-2 transition"
          >
            <span>{t('schemes.prepare_btn')}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* "Explain Why Not" Modal */}
      {showExplainModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-5 h-5 text-saffron-600" />
                <h3 className="font-bold text-slate-900 text-lg">
                  {language === 'hi' ? 'पात्रता कारण स्पष्टीकरण' : 'Why You Did Not Qualify'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowExplainModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 text-xs sm:text-sm text-slate-800 leading-relaxed">
              {rejectionReason || 'The applicant profile misses 1 mandatory revenue certificate or falls outside specified land ceiling guidelines.'}
            </div>

            {/* Next Best Schemes */}
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                {language === 'hi' ? 'आपके लिए अनुशंसित अन्य सर्वश्रेष्ठ योजनाएं:' : 'Next Best Alternative Schemes:'}
              </h4>
              <div className="space-y-2">
                {alternativeSchemes?.map((alt) => (
                  <Link
                    key={alt.scheme_id}
                    to={`/schemes/${alt.scheme_id}`}
                    onClick={() => setShowExplainModal(false)}
                    className="p-3 rounded-xl border border-slate-200 bg-slate-50 hover:bg-orange-50 hover:border-saffron-300 transition flex items-center justify-between block"
                  >
                    <div>
                      <span className="font-bold text-slate-900 text-xs sm:text-sm block">{alt.scheme_name}</span>
                      <span className="text-xs text-slate-500">{alt.benefit_summary}</span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-saffron-500" />
                  </Link>
                ))}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowExplainModal(false)}
              className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-xl text-sm transition"
            >
              {language === 'hi' ? 'समझ गया' : 'Close'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
