import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { SchemeUpdate } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/common/UIStates';
import {
  Bell,
  RefreshCw,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  Sparkles,
  ExternalLink
} from 'lucide-react';

export const Updates: React.FC = () => {
  const { t, language } = useLanguage();

  const [activeTab, setActiveTab] = useState<'changes' | 'upcoming'>('changes');
  const [updates, setUpdates] = useState<SchemeUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [notifiedPortals, setNotifiedPortals] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadUpdates();
  }, []);

  const loadUpdates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getSchemeUpdates();
      setUpdates(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load updates.');
    } finally {
      setLoading(false);
    }
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await new Promise((r) => setTimeout(r, 600));
    await loadUpdates();
    setIsRefreshing(false);
  };

  const toggleNotify = (portalId: string) => {
    setNotifiedPortals((prev) => ({ ...prev, [portalId]: !prev[portalId] }));
  };

  // Upcoming portals mock dataset
  const UPCOMING_PORTALS = [
    {
      id: 'port_01',
      title: 'Haryana Post-Matric SC/BC Scholarship 2026-27',
      openingDate: '15 April 2026',
      daysLeft: 27,
      portal: 'harchhatravritti.highereduhry.ac.in',
      benefits: 'Full tuition fee reimbursement + ₹10,000 allowance',
    },
    {
      id: 'port_02',
      title: 'PM Vishwakarma Toolkit & Loan Window',
      openingDate: '01 May 2026',
      daysLeft: 43,
      portal: 'pmvishwakarma.gov.in',
      benefits: '₹15,000 digital incentive for toolkits + ₹1L loan at 5%',
    },
    {
      id: 'port_03',
      title: 'Pradhan Mantri Fasal Bima Kharif Cycle',
      openingDate: '01 June 2026',
      daysLeft: 74,
      portal: 'pmfby.gov.in',
      benefits: 'Subsidized crop loss insurance cover for Kharif harvest',
    },
  ];

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'राजपत्र व पोर्टल बदलाव लोड हो रहे हैं...' : 'Scanning government gazette diffs and AI policy changefeeds...'} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadUpdates} />;
  }

  return (
    <div className="space-y-6">
      {/* Top Header with Last Checked & Manual Refresh */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            {language === 'hi' ? 'योजना बदलाव व आगामी पोर्टल' : 'AI-Detected Scheme Updates & Portals'}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5 flex items-center gap-2">
            <Clock className="w-3.5 h-3.5" />
            <span>{language === 'hi' ? 'अंतिम जांच: 10 मिनट पहले' : 'Last checked: 10 minutes ago via Gazette Feed'}</span>
          </p>
        </div>

        <button
          type="button"
          onClick={handleManualRefresh}
          disabled={isRefreshing}
          className="min-h-[44px] px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition"
        >
          <RefreshCw className={`w-4 h-4 text-saffron-600 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>{isRefreshing ? (language === 'hi' ? 'जांच हो रही है...' : 'Checking...') : (language === 'hi' ? 'पुनः जांचें' : 'Refresh Now')}</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-2xl px-3 pt-2">
        <button
          type="button"
          onClick={() => setActiveTab('changes')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'changes'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'हालिया बदलाव (AI Diff)' : 'Recent Changes'} ({updates.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('upcoming')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'upcoming'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'आगामी पोर्टल विंडो' : 'Upcoming Portals'} ({UPCOMING_PORTALS.length})
        </button>
      </div>

      {/* Tab 1: AI Detected Changes Feed */}
      {activeTab === 'changes' && (
        <div className="space-y-4">
          {updates.map((upd) => (
            <div
              key={upd.id}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition p-5 space-y-3"
            >
              {/* Card Header: Date & Affects You badge */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">
                  {language === 'hi' ? 'पहचाना गया:' : 'Detected on:'} {upd.detected_on}
                </span>

                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    upd.affects_user
                      ? 'bg-orange-100 text-saffron-800 border border-saffron-200'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {upd.affects_user
                    ? (language === 'hi' ? '★ आपकी पात्रता प्रभावित' : '★ Affects your profile')
                    : (language === 'hi' ? 'आप पर लागू नहीं' : 'Not relevant to you')}
                </span>
              </div>

              {/* Summary */}
              <div className="flex items-start gap-2.5">
                <Sparkles className="w-5 h-5 text-saffron-500 shrink-0 mt-0.5" />
                <h3 className="font-bold text-slate-900 text-base leading-snug">
                  {upd.summary}
                </h3>
              </div>

              {/* Before and After Comparison Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {/* Before */}
                <div className="p-3 bg-red-50/50 rounded-xl border border-red-100">
                  <span className="text-[11px] font-bold text-red-600 uppercase tracking-wider block mb-1">
                    {language === 'hi' ? 'पहले का नियम (Before)' : 'Previous Rule'}
                  </span>
                  <p className="text-xs sm:text-sm text-slate-700">
                    {upd.before}
                  </p>
                </div>

                {/* After */}
                <div className="p-3 bg-green-50/50 rounded-xl border border-green-200">
                  <span className="text-[11px] font-bold text-gov-green uppercase tracking-wider block mb-1">
                    {language === 'hi' ? 'नया नियम (After - Updated)' : 'New Updated Rule'}
                  </span>
                  <p className="text-xs sm:text-sm text-slate-900 font-semibold">
                    {upd.after}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Upcoming Portals */}
      {activeTab === 'upcoming' && (
        <div className="space-y-4">
          {UPCOMING_PORTALS.map((portal) => {
            const isNotified = !!notifiedPortals[portal.id];

            return (
              <div
                key={portal.id}
                className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div>
                  <h3 className="font-bold text-slate-900 text-base">
                    {portal.title}
                  </h3>
                  <p className="text-xs text-slate-600 mt-1">
                    {portal.benefits}
                  </p>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-2">
                    <span className="flex items-center gap-1 font-semibold text-slate-700">
                      <Calendar className="w-3.5 h-3.5 text-saffron-600" />
                      {portal.openingDate}
                    </span>
                    <span>•</span>
                    <span className="text-saffron-700 font-bold bg-orange-50 px-2 py-0.5 rounded">
                      {portal.daysLeft} {language === 'hi' ? 'दिन शेष' : 'days left'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleNotify(portal.id)}
                    className={`min-h-[44px] px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-1.5 transition ${
                      isNotified
                        ? 'bg-green-50 text-gov-green border border-green-200'
                        : 'bg-saffron-500 hover:bg-saffron-600 text-white shadow-xs'
                    }`}
                  >
                    <Bell className="w-4 h-4" />
                    <span>{isNotified ? (language === 'hi' ? 'अलर्ट चालू है' : 'Alert Active') : (language === 'hi' ? 'पोर्टल खुलते ही बताएं' : 'Notify Me')}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
