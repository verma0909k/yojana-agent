import React, { useState, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../api';
import { Notification, Draft } from '../types';
import { LoadingState, EmptyState, ErrorState } from '../components/common/UIStates';
import {
  Bell,
  Mail,
  Send,
  Trash2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Sliders,
  X,
  FileCheck,
  ShieldCheck,
  Sparkles,
  Edit2,
  Check
} from 'lucide-react';

export const Alerts: React.FC = () => {
  const { t, language } = useLanguage();

  const [activeTab, setActiveTab] = useState<'notifications' | 'drafts'>('notifications');
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Settings drawer state
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [channels, setChannels] = useState({
    email: true,
    telegram: true,
    sms: false,
  });
  const [reminderTiming, setReminderTiming] = useState('7d');

  // Drafts editing state
  const [editingDraftId, setEditingDraftId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState<string>('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [notifs, drfts] = await Promise.all([
        api.getNotifications(),
        api.getDrafts(),
      ]);
      setNotifications(notifs);
      setDrafts(drfts);
    } catch (err: any) {
      setError(err?.message || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    await api.markNotificationRead(id);
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const handleApproveDraft = async (id: string) => {
    await api.updateDraft(id, 'SENT');
    setDrafts((prev) =>
      prev.map((d) => (d.id === id ? { ...d, status: 'SENT' } : d))
    );
  };

  const handleDiscardDraft = async (id: string) => {
    await api.updateDraft(id, 'DISCARDED');
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  };

  const handleStartEditDraft = (draft: Draft) => {
    setEditingDraftId(draft.id);
    setEditBody(draft.body);
  };

  const handleSaveDraft = async (id: string) => {
    await api.updateDraft(id, 'PENDING_APPROVAL', editBody);
    setDrafts((prev) =>
      prev.map((d) => (d.id === id ? { ...d, body: editBody } : d))
    );
    setEditingDraftId(null);
  };

  if (loading) {
    return <LoadingState message={language === 'hi' ? 'अलर्ट एवं संदेश ड्राफ्ट लोड हो रहे हैं...' : 'Loading encrypted notifications and outbound message drafts...'} />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  const todayNotifs = notifications.filter((n) => n.created_at.includes('hours') || n.created_at.includes('ago') || n.created_at.includes('Today'));
  const earlierNotifs = notifications.filter((n) => !todayNotifs.includes(n));

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            {t('alerts.title')}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {language === 'hi'
              ? 'समय-सीमा व नवीनीकरण अलर्ट, तथा स्वीकृति योग्य संदेश ड्राफ्ट'
              : 'Citizen deadline monitoring and autonomous drafts with human-in-the-loop approval'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsSettingsOpen(true)}
          className="min-h-[44px] px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition"
        >
          <Sliders className="w-4 h-4 text-saffron-600" />
          <span>{language === 'hi' ? 'चैनल सेटिंग्स' : 'Channel Settings'}</span>
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-2xl px-3 pt-2">
        <button
          type="button"
          onClick={() => setActiveTab('notifications')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'notifications'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {language === 'hi' ? 'अलर्ट व सूचनाएं' : 'Notifications'} ({notifications.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('drafts')}
          className={`min-h-[44px] px-4 py-2 font-bold text-xs sm:text-sm border-b-2 transition ${
            activeTab === 'drafts'
              ? 'border-saffron-500 text-saffron-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          {t('alerts.drafts_tab')} ({drafts.filter((d) => d.status === 'PENDING_APPROVAL').length})
        </button>
      </div>

      {/* TAB 1: Notifications Grouped by Today and Earlier */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          {/* Today Group */}
          <div className="space-y-3">
            <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              {language === 'hi' ? 'आज (Today)' : 'Today'}
            </h2>

            {todayNotifs.map((notif) => {
              const isExpiry = notif.type === 'DOCUMENT_EXPIRY';
              const isDeadline = notif.type === 'DEADLINE';
              const isScheme = notif.type === 'SCHEME_CHANGE';

              return (
                <div
                  key={notif.id}
                  onClick={() => handleMarkRead(notif.id)}
                  className={`bg-white rounded-2xl border p-4 sm:p-5 shadow-xs flex items-start justify-between gap-3 cursor-pointer transition ${
                    notif.read ? 'border-slate-200' : 'border-saffron-300 bg-orange-50/20'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        isExpiry
                          ? 'bg-red-50 text-red-600'
                          : isDeadline
                          ? 'bg-amber-50 text-amber-600'
                          : isScheme
                          ? 'bg-blue-50 text-blue-600'
                          : 'bg-green-50 text-gov-green'
                      }`}
                    >
                      {isExpiry ? (
                        <AlertTriangle className="w-5 h-5" />
                      ) : isDeadline ? (
                        <Clock className="w-5 h-5" />
                      ) : (
                        <FileCheck className="w-5 h-5" />
                      )}
                    </div>

                    <div>
                      <p className={`text-xs sm:text-sm ${notif.read ? 'text-slate-700' : 'font-bold text-slate-900'}`}>
                        {notif.message}
                      </p>
                      <span className="text-[11px] text-slate-400 mt-1 block">
                        {notif.created_at}
                      </span>
                    </div>
                  </div>

                  {!notif.read && (
                    <span className="w-2.5 h-2.5 rounded-full bg-saffron-500 shrink-0 mt-1" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Earlier Group */}
          {earlierNotifs.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                {language === 'hi' ? 'पहले के (Earlier)' : 'Earlier'}
              </h2>

              {earlierNotifs.map((notif) => (
                <div
                  key={notif.id}
                  className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-xs flex items-start justify-between gap-3"
                >
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 text-slate-500 flex items-center justify-center shrink-0">
                      <FileCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-xs sm:text-sm text-slate-700">
                        {notif.message}
                      </p>
                      <span className="text-[11px] text-slate-400 mt-1 block">
                        {notif.created_at}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: AI Drafts with Approval Barrier */}
      {activeTab === 'drafts' && (
        <div className="space-y-4">
          {/* Clear Human-in-the-Loop Guarantee */}
          <div className="bg-orange-50 border border-saffron-200 rounded-2xl p-4 flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-saffron-600 shrink-0" />
            <span className="font-bold text-saffron-950 text-xs sm:text-sm">
              {t('alerts.disclaimer')}
            </span>
          </div>

          {drafts.length === 0 ? (
            <EmptyState
              title={language === 'hi' ? 'कोई ड्राफ्ट लंबित नहीं है' : 'No pending drafts'}
              description={language === 'hi' ? 'सभी संदेश स्वीकृत और भेजे जा चुके हैं।' : 'All autonomous email and Telegram drafts have been processed.'}
            />
          ) : (
            <div className="space-y-4">
              {drafts.map((draft) => {
                const isSent = draft.status === 'SENT';
                const isEditing = editingDraftId === draft.id;

                return (
                  <div
                    key={draft.id}
                    className="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-5 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase bg-slate-100 text-slate-700">
                          {draft.channel}
                        </span>
                        <span className="text-xs text-slate-500 font-medium">
                          {draft.created_at}
                        </span>
                      </div>

                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                          isSent
                            ? 'bg-green-100 text-gov-green'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {draft.status.replace('_', ' ')}
                      </span>
                    </div>

                    {/* Recipient & Subject */}
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs space-y-1">
                      <div>
                        <span className="font-semibold text-slate-500">{language === 'hi' ? 'प्राप्तकर्ता:' : 'To:'} </span>
                        <span className="font-bold text-slate-900">{draft.to}</span>
                      </div>
                      <div>
                        <span className="font-semibold text-slate-500">{language === 'hi' ? 'विषय:' : 'Subject:'} </span>
                        <span className="font-bold text-slate-900">{draft.subject}</span>
                      </div>
                    </div>

                    {/* Body */}
                    {isEditing ? (
                      <textarea
                        rows={6}
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        className="w-full p-3 text-xs sm:text-sm border border-saffron-500 rounded-xl focus:outline-none font-mono"
                      />
                    ) : (
                      <div className="p-3.5 bg-white rounded-xl border border-slate-200 text-xs sm:text-sm text-slate-700 whitespace-pre-line leading-relaxed font-sans">
                        {draft.body}
                      </div>
                    )}

                    {/* Action Buttons: Approve and Send, Edit, Discard */}
                    {!isSent && (
                      <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                        <button
                          type="button"
                          onClick={() => handleDiscardDraft(draft.id)}
                          className="text-xs font-semibold text-red-600 hover:text-red-700 flex items-center gap-1.5 py-2 px-3 rounded-lg hover:bg-red-50 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>{language === 'hi' ? 'रद्द करें' : 'Discard'}</span>
                        </button>

                        <div className="flex items-center gap-2">
                          {isEditing ? (
                            <button
                              type="button"
                              onClick={() => handleSaveDraft(draft.id)}
                              className="px-4 py-2 bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>{language === 'hi' ? 'बदलाव सहेजें' : 'Save edits'}</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleStartEditDraft(draft)}
                              className="min-h-[44px] px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs sm:text-sm font-semibold flex items-center gap-1.5 transition"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                              <span>{language === 'hi' ? 'संपादित करें' : 'Edit message'}</span>
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => handleApproveDraft(draft.id)}
                            className="min-h-[44px] px-5 py-2 bg-saffron-500 hover:bg-saffron-600 active:scale-[0.99] text-white rounded-xl text-xs sm:text-sm font-bold shadow-sm flex items-center gap-1.5 transition"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>{t('alerts.approve_send')}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Channel Settings Drawer */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-end z-50 animate-fade-in">
          <div className="bg-white max-w-md w-full h-full p-6 shadow-2xl flex flex-col justify-between overflow-y-auto">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Sliders className="w-5 h-5 text-saffron-600" />
                  <h3 className="font-bold text-slate-900 text-base">
                    {language === 'hi' ? 'अलर्ट व चैनल सेटिंग्स' : 'Notification Channel Settings'}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Channels toggles */}
              <div className="mt-6 space-y-4">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'सक्रिय सूचना चैनल' : 'Active Delivery Channels'}
                </span>

                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <span className="text-sm font-semibold text-slate-800">Email Alerts</span>
                  <input
                    type="checkbox"
                    checked={channels.email}
                    onChange={(e) => setChannels({ ...channels, email: e.target.checked })}
                    className="w-5 h-5 text-saffron-600 rounded"
                  />
                </label>

                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <span className="text-sm font-semibold text-slate-800">Telegram Bot Notifications</span>
                  <input
                    type="checkbox"
                    checked={channels.telegram}
                    onChange={(e) => setChannels({ ...channels, telegram: e.target.checked })}
                    className="w-5 h-5 text-saffron-600 rounded"
                  />
                </label>

                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50">
                  <span className="text-sm font-semibold text-slate-800">SMS Reminders</span>
                  <input
                    type="checkbox"
                    checked={channels.sms}
                    onChange={(e) => setChannels({ ...channels, sms: e.target.checked })}
                    className="w-5 h-5 text-saffron-600 rounded"
                  />
                </label>
              </div>

              {/* Timing */}
              <div className="mt-6 space-y-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                  {language === 'hi' ? 'अंतिम तिथि से कितने दिन पहले सूचित करें?' : 'Lead time before deadlines'}
                </span>
                <select
                  value={reminderTiming}
                  onChange={(e) => setReminderTiming(e.target.value)}
                  className="w-full p-3 rounded-xl border border-slate-300 text-sm font-semibold text-slate-800 bg-white"
                >
                  <option value="3d">3 days before deadline</option>
                  <option value="7d">7 days before deadline (Recommended)</option>
                  <option value="15d">15 days before deadline</option>
                </select>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsSettingsOpen(false)}
              className="w-full py-3 bg-saffron-500 hover:bg-saffron-600 text-white font-bold rounded-xl text-sm transition mt-6"
            >
              {language === 'hi' ? 'सेटिंग्स सहेजें' : 'Save Preferences'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
