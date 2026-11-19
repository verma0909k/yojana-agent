import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import {
  ShieldCheck,
  FileText,
  Bell,
  ArrowRight,
  CheckCircle2,
  Lock,
  Mic,
  UploadCloud,
  ChevronLeft
} from 'lucide-react';

export const Signup: React.FC = () => {
  const { t, language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [selectedLang, setSelectedLang] = useState<'en' | 'hi'>('en');

  // Consent states
  const [consentStoreDocs, setConsentStoreDocs] = useState(true);
  const [consentReminders, setConsentReminders] = useState(true);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [error, setError] = useState('');

  const handleStep1Submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError(language === 'hi' ? 'कृपया अपना नाम दर्ज करें' : 'Please enter your full name');
      return;
    }
    const cleanMobile = mobile.replace(/\D/g, '');
    if (cleanMobile.length !== 10) {
      setError(t('auth.invalid_phone'));
      return;
    }
    setError('');
    setLanguage(selectedLang);
    setStep(2);
  };

  const handleStep2Submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreeTerms) {
      setError(language === 'hi' ? 'आगे बढ़ने के लिए शर्तों से सहमत होना अनिवार्य है' : 'You must agree to the Terms and Privacy Policy to continue');
      return;
    }
    setError('');

    // Complete sign up and login
    auth.login(mobile, name);
    auth.updateUser({ language: selectedLang });
    setStep(3);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50/60 via-slate-50 to-white flex flex-col justify-between p-4 sm:p-6">
      {/* Top Header */}
      <div className="max-w-md w-full mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-saffron-500 flex items-center justify-center text-white font-bold shadow-md shadow-saffron-500/20">
            य
          </div>
          <span className="font-bold text-slate-900 text-lg">YojanaAgent</span>
        </div>

        {/* Language switch */}
        <div className="flex items-center bg-white border border-slate-200 rounded-lg p-0.5 shadow-sm text-xs font-medium">
          <button
            type="button"
            onClick={() => {
              setLanguage('en');
              setSelectedLang('en');
            }}
            className={`px-2.5 py-1 rounded-md transition ${language === 'en' ? 'bg-saffron-500 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
          >
            English
          </button>
          <button
            type="button"
            onClick={() => {
              setLanguage('hi');
              setSelectedLang('hi');
            }}
            className={`px-2.5 py-1 rounded-md transition ${language === 'hi' ? 'bg-saffron-500 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'}`}
          >
            हिंदी
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-md w-full mx-auto my-auto py-6">
        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
            <span className={step >= 1 ? 'text-saffron-600' : ''}>
              {language === 'hi' ? '१. विवरण' : '1. Profile'}
            </span>
            <span className={step >= 2 ? 'text-saffron-600' : ''}>
              {language === 'hi' ? '२. सहमति' : '2. Consent'}
            </span>
            <span className={step >= 3 ? 'text-saffron-600' : ''}>
              {language === 'hi' ? '३. शुरुआत' : '3. Welcome'}
            </span>
          </div>
          <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
            <div
              className="bg-saffron-500 h-full transition-all duration-300 rounded-full"
              style={{ width: step === 1 ? '33%' : step === 2 ? '66%' : '100%' }}
            />
          </div>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 border border-slate-100">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* STEP 1: Basic Details */}
          {step === 1 && (
            <div>
              <h1 className="text-2xl font-bold text-slate-900 mb-1">
                {t('signup.title')}
              </h1>
              <p className="text-sm text-slate-500 mb-6">
                {language === 'hi'
                  ? 'अपनी जानकारी दर्ज करें ताकि हम सही योजनाएं खोज सकें'
                  : 'Enter your basic details to find schemes you qualify for'}
              </p>

              <form onSubmit={handleStep1Submit} className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    {t('signup.name_label')}
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={language === 'hi' ? 'उदा. राजेश कुमार' : 'e.g. Ramesh Kumar'}
                    className="w-full px-4 py-3 border border-slate-300 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    {t('auth.mobile_label')}
                  </label>
                  <div className="flex">
                    <span className="inline-flex items-center px-3.5 rounded-l-xl border border-r-0 border-slate-300 bg-slate-50 text-slate-600 font-medium text-sm">
                      🇮🇳 +91
                    </span>
                    <input
                      type="tel"
                      maxLength={10}
                      required
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value.replace(/\D/g, ''))}
                      placeholder="98765 43210"
                      className="w-full px-4 py-3 border border-slate-300 rounded-r-xl text-base focus:outline-none focus:ring-2 focus:ring-saffron-500 focus:border-transparent transition tracking-wider"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    {language === 'hi' ? 'पसंदीदा भाषा' : 'Preferred Language'}
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedLang('en')}
                      className={`p-3 rounded-xl border text-left font-medium transition ${
                        selectedLang === 'en'
                          ? 'border-saffron-500 bg-orange-50/50 text-saffron-700 font-semibold'
                          : 'border-slate-200 text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="text-sm">English</div>
                      <div className="text-xs text-slate-500 font-normal">Primary default</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLang('hi')}
                      className={`p-3 rounded-xl border text-left font-medium transition ${
                        selectedLang === 'hi'
                          ? 'border-saffron-500 bg-orange-50/50 text-saffron-700 font-semibold'
                          : 'border-slate-200 text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="text-sm">हिंदी</div>
                      <div className="text-xs text-slate-500 font-normal">देवनागरी लिपि</div>
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full min-h-[48px] bg-saffron-500 hover:bg-saffron-600 active:scale-[0.99] text-white font-semibold rounded-xl text-base shadow-md shadow-saffron-500/20 transition flex items-center justify-center gap-2 mt-4"
                >
                  <span>{t('signup.next')}</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
              </form>
            </div>
          )}

          {/* STEP 2: Plain Language Consent */}
          {step === 2 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="p-1 -ml-2 text-slate-400 hover:text-slate-700 rounded-lg"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <h1 className="text-xl font-bold text-slate-900">
                  {t('signup.step2')}
                </h1>
              </div>
              <p className="text-sm text-slate-500 mb-6">
                {language === 'hi'
                  ? 'हम आपके अधिकारों का सम्मान करते हैं। आप तय करें कि आप क्या साझा करना चाहते हैं।'
                  : 'You are in full control. Choose how you want YojanaAgent to assist you.'}
              </p>

              <form onSubmit={handleStep2Submit} className="space-y-4">
                {/* Consent 1 */}
                <div
                  onClick={() => setConsentStoreDocs(!consentStoreDocs)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    consentStoreDocs ? 'border-saffron-300 bg-orange-50/40' : 'border-slate-200 bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={consentStoreDocs}
                      onChange={() => {}}
                      className="mt-1 w-5 h-5 rounded text-saffron-600 focus:ring-saffron-500"
                    />
                    <div>
                      <div className="flex items-center gap-1.5 font-semibold text-slate-900 text-sm">
                        <Lock className="w-4 h-4 text-saffron-600" />
                        <span>{t('signup.consent_storage')}</span>
                        <span className="text-xs font-normal text-slate-500">
                          ({language === 'hi' ? 'वैकल्पिक' : 'Optional'})
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        {t('signup.consent_storage_desc')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Consent 2 */}
                <div
                  onClick={() => setConsentReminders(!consentReminders)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    consentReminders ? 'border-saffron-300 bg-orange-50/40' : 'border-slate-200 bg-slate-50/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={consentReminders}
                      onChange={() => {}}
                      className="mt-1 w-5 h-5 rounded text-saffron-600 focus:ring-saffron-500"
                    />
                    <div>
                      <div className="flex items-center gap-1.5 font-semibold text-slate-900 text-sm">
                        <Bell className="w-4 h-4 text-saffron-600" />
                        <span>{t('signup.consent_reminders')}</span>
                        <span className="text-xs font-normal text-slate-500">
                          ({language === 'hi' ? 'वैकल्पिक' : 'Optional'})
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        {t('signup.consent_reminders_desc')}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Consent 3: Required Terms */}
                <div
                  onClick={() => setAgreeTerms(!agreeTerms)}
                  className={`p-4 rounded-xl border cursor-pointer transition ${
                    agreeTerms ? 'border-slate-400 bg-slate-50' : 'border-slate-200'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      required
                      checked={agreeTerms}
                      onChange={() => {}}
                      className="mt-1 w-5 h-5 rounded text-saffron-600 focus:ring-saffron-500"
                    />
                    <div>
                      <div className="font-semibold text-slate-900 text-sm">
                        {t('signup.agree_terms')}
                        <span className="text-red-500 ml-0.5">*</span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        {language === 'hi'
                          ? 'हम कभी भी आपका व्यक्तिगत डेटा किसी तीसरे पक्ष को नहीं बेचते। सारा डेटा सुरक्षित एन्क्रिप्शन में रहता है।'
                          : 'Your data is strictly encrypted and never sold or shared with unapproved third parties.'}
                      </p>
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full min-h-[48px] bg-saffron-500 hover:bg-saffron-600 active:scale-[0.99] text-white font-semibold rounded-xl text-base shadow-md shadow-saffron-500/20 transition flex items-center justify-center gap-2 mt-4"
                >
                  <span>{language === 'hi' ? 'सहमति दें और खाता बनाएं' : 'Agree & Create Account'}</span>
                  <CheckCircle2 className="w-5 h-5" />
                </button>
              </form>
            </div>
          )}

          {/* STEP 3: Welcome and Choices */}
          {step === 3 && (
            <div className="text-center py-2">
              <div className="w-16 h-16 bg-green-100 text-gov-green rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-9 h-9" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-2">
                {language === 'hi' ? `स्वागत है, ${name}!` : `Welcome, ${name}!`}
              </h1>
              <p className="text-sm text-slate-600 mb-8 leading-relaxed">
                {language === 'hi'
                  ? 'आपका खाता तैयार है। सरकारी योजनाओं का लाभ पाने के लिए आप कैसे शुरुआत करना चाहते हैं?'
                  : 'Your account is ready. How would you like to discover government schemes tailored for you?'}
              </p>

              <div className="space-y-3">
                <button
                  onClick={() => navigate('/')}
                  className="w-full p-4 rounded-xl border-2 border-saffron-500 bg-orange-50/50 hover:bg-orange-50 text-left transition flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-xl bg-saffron-500 text-white flex items-center justify-center shrink-0 shadow-sm">
                      <Mic className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-base group-hover:text-saffron-600 transition">
                        {t('signup.describe_choice')}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {language === 'hi'
                          ? 'अपनी स्थिति बोलकर या लिखकर तुरंत 500+ योजनाएं जांचें'
                          : 'Speak or type your profile to run AI semantic search'}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-saffron-500 group-hover:translate-x-1 transition" />
                </button>

                <button
                  onClick={() => navigate('/documents')}
                  className="w-full p-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-white text-left transition flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center shrink-0">
                      <UploadCloud className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-base">
                        {t('signup.upload_choice')}
                      </div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {language === 'hi'
                          ? 'आधार, आय या राशन कार्ड अपलोड करें - AI विवरण निकाल लेगा'
                          : 'Upload Aadhaar, income or ration card for instant parsing'}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-slate-400 group-hover:translate-x-1 transition" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Link */}
        {step < 3 && (
          <div className="mt-6 text-center text-sm text-slate-600">
            {language === 'hi' ? 'पहले से खाता है?' : 'Already have an account?'}{' '}
            <Link to="/login" className="font-semibold text-saffron-600 hover:text-saffron-700 underline">
              {language === 'hi' ? 'लॉग इन करें' : 'Log in'}
            </Link>
          </div>
        )}
      </div>

      {/* Trust Footer */}
      <div className="max-w-md w-full mx-auto text-center text-xs text-slate-500 py-2 flex items-center justify-center gap-1.5">
        <ShieldCheck className="w-4 h-4 text-gov-green" />
        <span>{language === 'hi' ? 'नागरिक डेटा पूर्ण रूप से सुरक्षित एवं एन्क्रिप्टेड है' : 'Citizen privacy protected under DPDP Act'}</span>
      </div>
    </div>
  );
};
