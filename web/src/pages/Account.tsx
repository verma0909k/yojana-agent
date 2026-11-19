import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import {
  User,
  Phone,
  Mail,
  Globe,
  CheckCircle2,
  Shield,
  Smartphone,
  Laptop,
  LogOut,
  Edit2,
  Check,
  ArrowRight,
  KeyRound
} from 'lucide-react';

export const Account: React.FC = () => {
  const { t, language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const [user, setUser] = useState(auth.getCurrentUser() || {
    id: 'usr_demo_101',
    name: 'Ananya Verma',
    phone: '98765 12345',
    email: 'ananya.verma@example.com',
    language: 'en',
    verified: true,
  });

  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [nameInput, setNameInput] = useState(user.name);
  const [emailInput, setEmailInput] = useState(user.email || '');

  // Change phone number flow
  const [showPhoneModal, setShowPhoneModal] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [phoneOtp, setPhoneOtp] = useState('');
  const [phoneStep, setPhoneStep] = useState<1 | 2>(1);

  // Active sessions
  const [otherSessionsLoggedOut, setOtherSessionsLoggedOut] = useState(false);

  const handleSaveProfile = () => {
    auth.updateUser({ name: nameInput, email: emailInput });
    setUser({ ...user, name: nameInput, email: emailInput });
    setIsEditingProfile(false);
  };

  const handleSendPhoneOtp = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPhone.replace(/\D/g, '').length === 10) {
      setPhoneStep(2);
    }
  };

  const handleVerifyPhoneOtp = (e: React.FormEvent) => {
    e.preventDefault();
    auth.updateUser({ phone: newPhone });
    setUser({ ...user, phone: newPhone });
    setShowPhoneModal(false);
    setPhoneStep(1);
    setNewPhone('');
  };

  const handleLogoutOtherDevices = () => {
    setOtherSessionsLoggedOut(true);
  };

  const handleLogout = () => {
    auth.logout();
    navigate('/login');
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Page Title */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
          {language === 'hi' ? 'खाता एवं सुरक्षा' : 'Account & Security Settings'}
        </h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {language === 'hi'
            ? 'अपनी प्रोफ़ाइल, सत्यापित मोबाइल नंबर एवं सक्रिय सत्र प्रबंधित करें'
            : 'Manage verified citizen credentials, linked accounts, and active device sessions'}
        </p>
      </div>

      {/* Profile Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-orange-100 text-saffron-700 flex items-center justify-center font-bold text-xl shadow-xs">
              {user.name.charAt(0)}
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">{user.name}</h2>
              <span className="text-xs text-slate-500">Citizen ID: {user.id}</span>
            </div>
          </div>

          {!isEditingProfile && (
            <button
              type="button"
              onClick={() => setIsEditingProfile(true)}
              className="text-xs font-semibold text-saffron-600 hover:text-saffron-700 flex items-center gap-1.5 py-1.5 px-3 rounded-lg hover:bg-orange-50 transition"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>{language === 'hi' ? 'संपादित करें' : 'Edit profile'}</span>
            </button>
          )}
        </div>

        {isEditingProfile ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                {language === 'hi' ? 'पूरा नाम' : 'Full Name'}
              </label>
              <input
                type="text"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                className="w-full p-2.5 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-saffron-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                {language === 'hi' ? 'ईमेल पता' : 'Email Address'}
              </label>
              <input
                type="email"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                className="w-full p-2.5 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-saffron-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsEditingProfile(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600"
              >
                {language === 'hi' ? 'रद्द करें' : 'Cancel'}
              </button>
              <button
                type="button"
                onClick={handleSaveProfile}
                className="px-5 py-2 bg-saffron-500 text-white rounded-xl text-xs font-bold shadow-xs"
              >
                {language === 'hi' ? 'सहेजें' : 'Save Changes'}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
            {/* Phone */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Phone className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-[11px] text-slate-500 block">{language === 'hi' ? 'मोबाइल नंबर' : 'Mobile Number'}</span>
                  <span className="font-bold text-slate-900">+91 {user.phone}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-gov-green flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Verified</span>
                </span>
                <button
                  type="button"
                  onClick={() => setShowPhoneModal(true)}
                  className="text-xs text-saffron-600 font-semibold underline"
                >
                  Change
                </button>
              </div>
            </div>

            {/* Email */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Mail className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-[11px] text-slate-500 block">{language === 'hi' ? 'ईमेल' : 'Email Address'}</span>
                  <span className="font-bold text-slate-900">{user.email || 'None added'}</span>
                </div>
              </div>
            </div>

            {/* Language */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Globe className="w-4 h-4 text-slate-400" />
                <div>
                  <span className="text-[11px] text-slate-500 block">{language === 'hi' ? 'भाषा प्राथमिकता' : 'Language'}</span>
                  <span className="font-bold text-slate-900">{language === 'hi' ? 'हिंदी (Devanagari)' : 'English (India)'}</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
                className="text-xs text-saffron-600 font-semibold underline"
              >
                Switch
              </button>
            </div>

            {/* Linked Google */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="font-bold text-slate-600">G</span>
                <div>
                  <span className="text-[11px] text-slate-500 block">{language === 'hi' ? 'लिंक्ड अकाउंट' : 'Linked Account'}</span>
                  <span className="font-bold text-slate-900">Google Connected</span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700">
                Linked
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Active Sessions Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-gov-green" />
            <h3 className="font-bold text-slate-900 text-base">
              {language === 'hi' ? 'सक्रिय सत्र एवं उपकरण' : 'Active Login Sessions'}
            </h3>
          </div>

          <button
            type="button"
            onClick={handleLogoutOtherDevices}
            disabled={otherSessionsLoggedOut}
            className="text-xs font-semibold text-red-600 hover:text-red-700 disabled:opacity-50"
          >
            {otherSessionsLoggedOut
              ? (language === 'hi' ? 'सभी अन्य उपकरण लॉग आउट हुए' : 'All other devices signed out')
              : (language === 'hi' ? 'अन्य सभी उपकरणों से लॉग आउट करें' : 'Log out of other devices')}
          </button>
        </div>

        <div className="space-y-2.5 text-xs">
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Laptop className="w-4 h-4 text-slate-600" />
              <div>
                <span className="font-bold text-slate-900 block">Chrome on Windows (This Device)</span>
                <span className="text-slate-500">New Delhi, India • Active now</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-green-100 text-gov-green">
              Current
            </span>
          </div>

          {!otherSessionsLoggedOut && (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Smartphone className="w-4 h-4 text-slate-600" />
                <div>
                  <span className="font-bold text-slate-900 block">Mobile Safari (iPhone 14)</span>
                  <span className="text-slate-500">Chandigarh, India • 2 days ago</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Prominent Log out Button */}
      <div className="pt-2">
        <button
          type="button"
          onClick={handleLogout}
          className="w-full min-h-[48px] bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 font-bold rounded-xl text-sm sm:text-base flex items-center justify-center gap-2 transition"
        >
          <LogOut className="w-5 h-5" />
          <span>{t('nav.logout')}</span>
        </button>
      </div>

      {/* Change Phone Modal */}
      {showPhoneModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <h3 className="font-bold text-slate-900 text-base">
              {language === 'hi' ? 'मोबाइल नंबर बदलें' : 'Change Mobile Number'}
            </h3>

            {phoneStep === 1 ? (
              <form onSubmit={handleSendPhoneOtp} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {language === 'hi' ? 'नया 10-अंकों का मोबाइल नंबर' : 'New 10-digit Mobile Number'}
                  </label>
                  <input
                    type="tel"
                    required
                    maxLength={10}
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value.replace(/\D/g, ''))}
                    placeholder="98765 00000"
                    className="w-full p-2.5 border border-slate-300 rounded-xl text-sm"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowPhoneModal(false)}
                    className="px-3 py-1.5 text-xs text-slate-600"
                  >
                    {language === 'hi' ? 'रद्द करें' : 'Cancel'}
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-saffron-500 text-white rounded-xl text-xs font-bold"
                  >
                    {language === 'hi' ? 'ओटीपी भेजें' : 'Send OTP'}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={handleVerifyPhoneOtp} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    {language === 'hi' ? 'कोड दर्ज करें (डेमो 123456)' : 'Enter OTP (demo: 123456)'}
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={phoneOtp}
                    onChange={(e) => setPhoneOtp(e.target.value)}
                    placeholder="123456"
                    className="w-full p-2.5 border border-slate-300 rounded-xl text-center text-sm font-mono tracking-widest"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="submit"
                    className="w-full py-2 bg-gov-green text-white rounded-xl text-xs font-bold"
                  >
                    {language === 'hi' ? 'सत्यापित करें एवं अपडेट करें' : 'Verify & Update'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
