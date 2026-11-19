import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { MatchResult, VaultDocument } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/common/UIStates';
import {
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Heart,
  FileCheck,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Filter,
  Check,
  HelpCircle,
  Sparkles,
  ShieldCheck
} from 'lucide-react';

export const Schemes: React.FC = () => {
  const { t, language } = useLanguage();
  const navigate = useNavigate();

  const [schemes, setSchemes] = useState<MatchResult[]>([]);
  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & sorting
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'relevance' | 'benefit'>('relevance');

  // Interactive states
  const [savedSchemes, setSavedSchemes] = useState<Record<string, boolean>>({});
  const [expandedWhy, setExpandedWhy] = useState<Record<string, boolean>>({});
  const [inlineAnswers, setInlineAnswers] = useState<Record<string, string>>({});
  const [answeredKeys, setAnsweredKeys] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [schemeData, docData] = await Promise.all([
        api.getSchemes(),
        api.getDocuments(),
      ]);
      setSchemes(schemeData);
      setDocuments(docData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load eligible schemes.');
    } finally {
      setLoading(false);
    }
  };

  const toggleSave = (schemeId: string) => {
    setSavedSchemes((prev) => ({ ...prev, [schemeId]: !prev[schemeId] }));
  };

  const toggleExpandWhy = (schemeId: string) => {
    setExpandedWhy((prev) => ({ ...prev, [schemeId]: !prev[schemeId] }));
  };

  const handleInlineAnswerSubmit = (schemeId: string, field: string) => {
    setAnsweredKeys((prev) => ({ ...prev, [`${schemeId}_${field}`]: true }));
  };

  const handlePrepareApplication = async (schemeId: string) => {
    try {
      await api.createApplication(schemeId);
      navigate('/tracker');
    } catch (err) {
      console.error(err);
    }
  };

  // Helper to check if user has required document in vault
  const userHasDoc = (docName: string): boolean => {
    return documents.some(
      (d) =>
        d.doc_type.toLowerCase().includes(docName.toLowerCase()) ||
        docName.toLowerCase().includes(d.doc_type.toLowerCase())
    );
  };

  // Filtering & Sorting
  const categories = ['ALL', 'Education', 'Agriculture', 'Livelihood & Business', 'Healthcare'];

  const filteredSchemes = schemes.filter((s) => {
    if (selectedCategory !== 'ALL' && s.category !== selectedCategory) return false;
    return true;
  });

  const eligibleSchemes = filteredSchemes.filter((s) => s.status === 'ELIGIBLE');
  const almostSchemes = filteredSchemes.filter((s) => s.status === 'ALMOST');

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'आपकी पात्रता की जांच हो रही है...' : 'Evaluating gazette rules and computing matches...'} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Title & Summary */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            {language === 'hi' ? 'पात्र सरकारी योजनाएं' : 'Matched Government Schemes'}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {language === 'hi'
              ? 'आधिकारिक राजपत्र नियमों से सत्यापित योजनाएं। आप तुरंत आवेदन तैयार कर सकते हैं।'
              : 'Deterministic rule evaluations with 100% evidentiary backing.'}
          </p>
        </div>

        {/* Filter / Sort bar */}
        <div className="flex items-center gap-3">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="text-xs sm:text-sm bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-saffron-500"
          >
            <option value="relevance">{language === 'hi' ? 'प्रासंगिकता अनुसार' : 'Sort by Relevance'}</option>
            <option value="benefit">{language === 'hi' ? 'अधिकतम लाभ' : 'Highest Benefit'}</option>
          </select>
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        <Filter className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`min-h-[38px] px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap transition ${
              selectedCategory === cat
                ? 'bg-saffron-500 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {cat === 'ALL' ? (language === 'hi' ? 'सभी श्रेणियां' : 'All Categories') : cat}
          </button>
        ))}
      </div>

      {/* SECTION 1: You are Eligible */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gov-green" />
          <h2 className="text-lg font-bold text-slate-900">
            {t('schemes.eligible_title')} ({eligibleSchemes.length})
          </h2>
        </div>

        {eligibleSchemes.length === 0 ? (
          <EmptyState
            title={language === 'hi' ? 'कोई योजना नहीं मिली' : 'No matching schemes found'}
            description={language === 'hi' ? 'कृपया अपनी स्थिति में अधिक विवरण जोड़ें' : 'Try broadening your search query or selecting a different category.'}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {eligibleSchemes.map((scheme) => {
              const isSaved = !!savedSchemes[scheme.scheme_id];
              const isWhyOpen = !!expandedWhy[scheme.scheme_id];

              return (
                <div
                  key={scheme.scheme_id}
                  className="bg-white rounded-2xl border border-slate-200/90 shadow-xs hover:shadow-md transition-shadow p-5 flex flex-col justify-between"
                >
                  <div>
                    {/* Card Top: Badges & Heart */}
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-green-50 text-gov-green border border-green-200 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{language === 'hi' ? 'पूर्ण पात्र' : 'ELIGIBLE'}</span>
                        </span>

                        {scheme.needs_review && (
                          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                            <AlertCircle className="w-3.5 h-3.5" />
                            <span>{t('schemes.needs_review')}</span>
                          </span>
                        )}

                        <span className="text-xs text-slate-500 font-medium">
                          {scheme.category}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => toggleSave(scheme.scheme_id)}
                        className={`p-2 rounded-xl transition ${
                          isSaved ? 'text-red-500 bg-red-50' : 'text-slate-400 hover:text-slate-600 bg-slate-50'
                        }`}
                        title="Save scheme"
                      >
                        <Heart className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
                      </button>
                    </div>

                    {/* Scheme Name & Ministry */}
                    <Link
                      to={`/schemes/${scheme.scheme_id}`}
                      className="text-base sm:text-lg font-bold text-slate-900 hover:text-saffron-600 transition block leading-snug"
                    >
                      {scheme.scheme_name}
                    </Link>
                    <p className="text-xs text-slate-500 mt-1 mb-3">
                      {scheme.ministry}
                    </p>

                    {/* Benefit Summary Box */}
                    <div className="p-3 bg-orange-50/50 rounded-xl border border-saffron-100 text-xs sm:text-sm font-semibold text-slate-800 mb-4 flex items-start gap-2">
                      <Sparkles className="w-4 h-4 text-saffron-600 shrink-0 mt-0.5" />
                      <span>{scheme.benefit_summary}</span>
                    </div>

                    {/* Why You Qualify (Expandable) */}
                    <div className="mb-4">
                      <button
                        type="button"
                        onClick={() => toggleExpandWhy(scheme.scheme_id)}
                        className="text-xs font-bold text-slate-700 flex items-center justify-between w-full p-2 rounded-lg bg-slate-50 hover:bg-slate-100 transition"
                      >
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-gov-green" />
                          <span>{t('schemes.why_qualify')} ({scheme.satisfied_reasons.length})</span>
                        </span>
                        {isWhyOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isWhyOpen && (
                        <ul className="mt-2 space-y-1.5 pl-2 text-xs text-slate-600">
                          {scheme.satisfied_reasons.map((r, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-gov-green font-bold">✓</span>
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    {/* Documents Needed Checklist */}
                    <div className="mb-4">
                      <span className="text-xs font-bold text-slate-700 block mb-1.5">
                        {language === 'hi' ? 'आवश्यक दस्तावेज चेकलिस्ट:' : 'Documents Needed:'}
                      </span>
                      <div className="space-y-1.5">
                        {scheme.documents_required.map((docName, i) => {
                          const hasIt = userHasDoc(docName);
                          return (
                            <div key={i} className="flex items-center justify-between text-xs p-1.5 rounded-lg bg-slate-50 border border-slate-100">
                              <span className="text-slate-700 flex items-center gap-1.5">
                                <FileCheck className="w-3.5 h-3.5 text-slate-400" />
                                {docName}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  hasIt ? 'bg-green-100 text-gov-green' : 'bg-slate-200 text-slate-600'
                                }`}
                              >
                                {hasIt ? (language === 'hi' ? 'वॉल्ट में मौजूद' : 'In Vault') : (language === 'hi' ? 'आवश्यक' : 'Required')}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Card Bottom: Official Portal & Prepare Button */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2 mt-2">
                    <a
                      href={scheme.official_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1 py-2 px-2.5 rounded-lg hover:bg-slate-50 transition"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-gov-green" />
                      <span>{t('schemes.portal_verified')}</span>
                      <ExternalLink className="w-3 h-3 text-slate-400" />
                    </a>

                    <button
                      type="button"
                      onClick={() => handlePrepareApplication(scheme.scheme_id)}
                      className="min-h-[44px] px-4 py-2 bg-saffron-500 hover:bg-saffron-600 active:scale-[0.99] text-white text-xs sm:text-sm font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition"
                    >
                      <span>{t('schemes.prepare_btn')}</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: Almost Eligible */}
      {almostSchemes.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <h2 className="text-lg font-bold text-slate-900">
              {t('schemes.almost_title')} ({almostSchemes.length})
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {almostSchemes.map((scheme) => {
              const isSaved = !!savedSchemes[scheme.scheme_id];

              return (
                <div
                  key={scheme.scheme_id}
                  className="bg-white rounded-2xl border border-amber-200/80 shadow-xs hover:shadow-md transition p-5 flex flex-col justify-between"
                >
                  <div>
                    {/* Top Badges */}
                    <div className="flex items-start justify-between gap-3 mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" />
                          <span>{language === 'hi' ? 'लगभग पात्र' : 'ALMOST ELIGIBLE'}</span>
                        </span>
                        {scheme.needs_review && (
                          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                            {t('schemes.needs_review')}
                          </span>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => toggleSave(scheme.scheme_id)}
                        className={`p-2 rounded-xl transition ${
                          isSaved ? 'text-red-500 bg-red-50' : 'text-slate-400 hover:text-slate-600 bg-slate-50'
                        }`}
                      >
                        <Heart className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
                      </button>
                    </div>

                    <Link
                      to={`/schemes/${scheme.scheme_id}`}
                      className="text-base sm:text-lg font-bold text-slate-900 hover:text-saffron-600 transition block"
                    >
                      {scheme.scheme_name}
                    </Link>
                    <p className="text-xs text-slate-500 mt-1 mb-3">
                      {scheme.ministry}
                    </p>

                    <p className="text-xs sm:text-sm text-slate-700 mb-3">
                      {scheme.benefit_summary}
                    </p>

                    {/* Missing Fields Inline Answering */}
                    <div className="p-3 bg-amber-50/60 rounded-xl border border-amber-200/70 mb-4 space-y-2">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                        <HelpCircle className="w-4 h-4 text-amber-600" />
                        <span>{language === 'hi' ? '1 उत्तर देकर पात्रता अनलॉक करें:' : 'Answer 1 quick question to unlock eligibility:'}</span>
                      </div>

                      {scheme.missing_fields.map((field) => {
                        const answerKey = `${scheme.scheme_id}_${field}`;
                        const isAnswered = !!answeredKeys[answerKey];

                        return (
                          <div key={field} className="text-xs space-y-1">
                            <span className="font-semibold text-slate-700 block">
                              {field.replace(/_/g, ' ').toUpperCase()}:
                            </span>
                            {isAnswered ? (
                              <div className="flex items-center gap-1.5 text-gov-green font-bold bg-white p-2 rounded-lg border border-green-200">
                                <Check className="w-4 h-4" />
                                <span>{language === 'hi' ? 'दर्ज कर लिया गया - पात्रता पुनः जांची जा रही है' : 'Answer recorded - re-evaluating rules'}</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  placeholder={language === 'hi' ? 'उत्तर दर्ज करें...' : 'Type detail here...'}
                                  value={inlineAnswers[answerKey] || ''}
                                  onChange={(e) =>
                                    setInlineAnswers((prev) => ({ ...prev, [answerKey]: e.target.value }))
                                  }
                                  className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded-lg text-xs focus:ring-1 focus:ring-saffron-500"
                                />
                                <button
                                  type="button"
                                  onClick={() => handleInlineAnswerSubmit(scheme.scheme_id, field)}
                                  className="px-3 py-1.5 bg-saffron-500 text-white font-bold rounded-lg text-xs hover:bg-saffron-600 whitespace-nowrap"
                                >
                                  {language === 'hi' ? 'सहेजें' : 'Save'}
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Bottom Action */}
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <a
                      href={scheme.official_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1 py-2 px-2.5 rounded-lg"
                    >
                      <ShieldCheck className="w-3.5 h-3.5 text-gov-green" />
                      <span>{t('schemes.portal_verified')}</span>
                    </a>

                    <Link
                      to={`/schemes/${scheme.scheme_id}`}
                      className="min-h-[44px] px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs sm:text-sm font-semibold rounded-xl flex items-center gap-1 transition"
                    >
                      <span>{language === 'hi' ? 'नियम देखें' : 'View Rules'}</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
