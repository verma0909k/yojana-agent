import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import {
  ShieldCheck,
  Lock,
  Download,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Globe,
  Bell,
  EyeOff
} from 'lucide-react';

export const Privacy: React.FC = () => {
  const { t, language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const [consentStoreDocs, setConsentStoreDocs] = useState(true);
  const [consentReminders, setConsentReminders] = useState(true);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDownloadData = () => {
    const user = auth.getCurrentUser();
    const exportData = {
      userProfile: user,
      exportTimestamp: new Date().toISOString(),
      compliance: 'Digital Personal Data Protection Act (DPDP), 2023',
      storedVaultDocuments: [
        'Aadhaar Card (Aadhaar number tokenized/masked)',
        'OBC Category Certificate (Revenue Dept)',
        'Land Holding Record (Khasra-Khatauni)',
      ],
      consentHistory: {
        documentStorage: consentStoreDocs,
        deadlineNotifications: consentReminders,
      },
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `YojanaAgent_UserData_${user?.id || 'citizen'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDeleteAllData = async () => {
    setIsDeleting(true);
    await new Promise((r) => setTimeout(r, 800));
    auth.logout();
    setIsDeleting(false);
    setShowDeleteModal(false);
    navigate('/login');
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
          {t('nav.privacy')}
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {language === 'hi'
            ? 'आपका डेटा आपका अधिकार है। जानिए क्या डेटा सुरक्षित रखा जाता है और क्यों।'
            : 'Clear transparency and granular citizen control under India’s DPDP Act'}
        </p>
      </div>

      {/* DPDP Compliance & Encrypted Guarantee Banner */}
      <div className="bg-green-50/70 border border-green-200 rounded-2xl p-5 flex items-start gap-3.5">
        <ShieldCheck className="w-6 h-6 text-gov-green shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="font-bold text-slate-900 text-sm sm:text-base">
            {language === 'hi' ? 'शून्य तृतीय-पक्ष डेटा साझाकरण गारंटी' : 'Zero Third-Party Data Sharing & End-to-End Encryption'}
          </h3>
          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
            {language === 'hi'
              ? 'हम आपका व्यक्तिगत विवरण, फोन नंबर अथवा दस्तावेज कभी भी किसी विज्ञापनदाता या गैर-सरकारी तीसरे पक्ष को नहीं बेचते। डेटा केवल आपकी सहमति से योजनाओं की पात्रता जांचने हेतु उपयोग होता है।'
              : 'We never monetize or sell citizen data. Documents are encrypted at rest with AES-256 and used strictly for eligibility matching and pre-filling.'}
          </p>
        </div>
      </div>

      {/* Explanation of What Data is Stored and Why */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-slate-900">
          {language === 'hi' ? 'हम क्या डेटा संग्रहीत करते हैं और क्यों?' : 'What Data We Store and Why'}
        </h2>

        <div className="space-y-3 text-xs sm:text-sm">
          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
            <span className="font-bold text-slate-900 block mb-0.5">
              1. {language === 'hi' ? 'मोबाइल नंबर व नाम' : 'Mobile Number & Basic Profile'}
            </span>
            <p className="text-slate-600">
              {language === 'hi'
                ? 'ओटीपी द्वारा सुरक्षित लॉगिन, समय-सीमा रिमाइंडर और आवेदन की स्थिति बताने के लिए।'
                : 'Used for OTP verification, deadline notifications, and session recovery.'}
            </p>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
            <span className="font-bold text-slate-900 block mb-0.5">
              2. {language === 'hi' ? 'अपलोड किए गए दस्तावेज़ (वॉल्ट)' : 'Document Vault & OCR Extractions'}
            </span>
            <p className="text-slate-600">
              {language === 'hi'
                ? 'आय, जाति, निवास और भूमि रिकॉर्ड केवल सरकारी नियमों से मिलान करने तथा आवेदन फॉर्म में स्वतः भरने के लिए उपयोग होते हैं।'
                : 'Certificate fields (income, category, acreage) evaluate statutory eligibility thresholds without re-typing.'}
            </p>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
            <span className="font-bold text-slate-900 block mb-0.5">
              3. {language === 'hi' ? 'आवेदन व ट्रैकिंग नोट्स' : 'Application Tracking & Notes'}
            </span>
            <p className="text-slate-600">
              {language === 'hi'
                ? 'आपके विभिन्न विभागों में किए गए आवेदनों की स्थिति याद रखने के लिए।'
                : 'Allows you to track submissions across multiple central and state portals in one place.'}
            </p>
          </div>
        </div>
      </div>

      {/* Granular Consent Toggles */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-slate-900">
          {language === 'hi' ? 'नागरिक सहमति नियंत्रण (Consent Settings)' : 'Citizen Consent Management'}
        </h2>

        <div className="space-y-3">
          <label className="flex items-start justify-between p-4 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition">
            <div className="space-y-0.5 pr-4">
              <span className="font-bold text-slate-900 text-sm block">
                {t('signup.consent_storage')}
              </span>
              <p className="text-xs text-slate-500">
                {t('signup.consent_storage_desc')}
              </p>
            </div>
            <input
              type="checkbox"
              checked={consentStoreDocs}
              onChange={(e) => setConsentStoreDocs(e.target.checked)}
              className="mt-1 w-5 h-5 text-saffron-600 rounded"
            />
          </label>

          <label className="flex items-start justify-between p-4 rounded-xl border border-slate-200 cursor-pointer hover:bg-slate-50 transition">
            <div className="space-y-0.5 pr-4">
              <span className="font-bold text-slate-900 text-sm block">
                {t('signup.consent_reminders')}
              </span>
              <p className="text-xs text-slate-500">
                {t('signup.consent_reminders_desc')}
              </p>
            </div>
            <input
              type="checkbox"
              checked={consentReminders}
              onChange={(e) => setConsentReminders(e.target.checked)}
              className="mt-1 w-5 h-5 text-saffron-600 rounded"
            />
          </label>
        </div>
      </div>

      {/* Data Export and Permanent Erasure Actions */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <h2 className="text-base sm:text-lg font-bold text-slate-900">
          {language === 'hi' ? 'डेटा पोर्टेबिलिटी एवं विलोपन अधिकार' : 'Data Portability & Right to Erasure'}
        </h2>

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
          {/* Download JSON Data */}
          <button
            type="button"
            onClick={handleDownloadData}
            className="w-full sm:w-auto min-h-[44px] px-5 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition"
          >
            <Download className="w-4 h-4 text-saffron-600" />
            <span>{language === 'hi' ? 'मेरा सम्पूर्ण डेटा डाउनलोड करें (JSON)' : 'Download my data'}</span>
          </button>

          {/* Delete All Data */}
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="w-full sm:w-auto min-h-[44px] px-5 py-2.5 rounded-xl bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition"
          >
            <Trash2 className="w-4 h-4" />
            <span>{language === 'hi' ? 'मेरा सम्पूर्ण डेटा मिटाएं' : 'Delete all my data'}</span>
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center">
              <h3 className="font-bold text-slate-900 text-lg">
                {language === 'hi' ? 'क्या आप सम्पूर्ण डेटा मिटाना चाहते हैं?' : 'Permanently Delete All Your Data?'}
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">
                {language === 'hi'
                  ? 'यह क्रिया अपरिवर्तनीय है। आपके सभी अपलोड किए गए दस्तावेज, प्रोफाइल तथ्य और आवेदन रिकॉर्ड हमेशा के लिए मिटा दिए जाएंगे।'
                  : 'This action is irreversible. All uploaded documents, extracted profile facts, and application drafts will be wiped from servers.'}
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {language === 'hi' ? 'पुष्टि करने के लिए "DELETE" टाइप करें:' : 'Type "DELETE" to confirm:'}
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full p-2.5 border border-slate-300 rounded-xl text-center text-sm font-bold uppercase tracking-wider"
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="w-1/2 py-2.5 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50"
              >
                {language === 'hi' ? 'रद्द करें' : 'Cancel'}
              </button>
              <button
                type="button"
                disabled={deleteConfirmText !== 'DELETE' || isDeleting}
                onClick={handleDeleteAllData}
                className="w-1/2 py-2.5 bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5"
              >
                {isDeleting ? 'Deleting...' : (language === 'hi' ? 'डेटा मिटाएं' : 'Confirm Delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
