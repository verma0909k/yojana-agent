import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import { api } from '../api';
import { Globe, ArrowRight, ShieldCheck, AlertCircle, X, Mail } from 'lucide-react';

export const Login: React.FC = () => {
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();

  const [mobileNumber, setMobileNumber] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // Google / Email custom modal states
  const [showGoogleModal, setShowGoogleModal] = useState(false);
  const [googleEmail, setGoogleEmail] = useState('');
  const [googleName, setGoogleName] = useState('');
  const [googleError, setGoogleError] = useState<string | null>(null);

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (attempts >= 5) {
      setError(t('auth.too_many_attempts'));
      return;
    }

    const cleanNum = mobileNumber.replace(/\D/g, '');
    if (cleanNum.length !== 10) {
      setError(t('auth.invalid_phone'));
      setAttempts((prev) => prev + 1);
      return;
    }

    setIsLoading(true);

    try {
      // Dispatches OTP to backend service / SMS gateway
      await api.sendOtp(cleanNum);
      sessionStorage.setItem('yojana_pending_phone', `+91 ${cleanNum.slice(0, 5)} ${cleanNum.slice(5)}`);
      setIsLoading(false);
      navigate('/verify', {
        state: {
          phone: `+91 ${cleanNum.slice(0, 5)} ${cleanNum.slice(5)}`,
        },
      });
    } catch {
      setIsLoading(false);
      sessionStorage.setItem('yojana_pending_phone', `+91 ${cleanNum.slice(0, 5)} ${cleanNum.slice(5)}`);
      navigate('/verify', {
        state: {
          phone: `+91 ${cleanNum.slice(0, 5)} ${cleanNum.slice(5)}`,
        },
      });
    }
  };

  const handleGoogleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setGoogleError(null);

    if (!googleEmail || !googleEmail.includes('@')) {
      setGoogleError('Please enter a valid email address (e.g. name@gmail.com).');
      return;
    }

    // Login with the citizen's actual email & name
    auth.loginWithEmail(googleEmail, googleName);
    setShowGoogleModal(false);
    const returnUrl = auth.getReturnUrl();
    navigate(returnUrl);
  };

  const handleDemoLogin = () => {
    auth.loginWithDemo();
    const returnUrl = auth.getReturnUrl();
    navigate(returnUrl);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-saffron-50 via-white to-slate-50 flex flex-col justify-between p-4 sm:p-6">
      {/* Top Bar with Language Toggle */}
      <div className="max-w-md w-full mx-auto flex items-center justify-between py-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-saffron flex items-center justify-center text-white font-bold text-sm">
            य
          </div>
          <span className="font-bold text-slate-900 tracking-tight">YojanaAgent</span>
        </div>

        <button
          onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 transition min-h-[44px]"
        >
          <Globe className="w-3.5 h-3.5 text-saffron" />
          <span>{language === 'en' ? 'हिंदी' : 'English'}</span>
        </button>
      </div>

      {/* Main Centered Login Card */}
      <div className="max-w-md w-full mx-auto my-auto py-8">
        <div className="bg-white rounded-card shadow-soft-hover border border-slate-200 p-6 sm:p-8">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-slate-900 mb-1">{t('app.name')}</h1>
            <p className="text-sm text-slate-600 font-medium">{t('app.tagline')}</p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2.5 text-danger text-sm">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Mobile Login Form */}
          <form onSubmit={handleSendOtp} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-800 mb-1.5">
                {t('auth.mobile_label')}
              </label>
              <div className="flex rounded-lg border border-slate-300 focus-within:border-saffron focus-within:ring-2 focus-within:ring-saffron/20 transition overflow-hidden">
                <span className="bg-slate-100 text-slate-600 px-3.5 py-3 text-sm font-semibold border-r border-slate-200 flex items-center min-h-[48px]">
                  +91
                </span>
                <input
                  type="tel"
                  maxLength={10}
                  placeholder="98765 43210"
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value.replace(/\D/g, ''))}
                  className="flex-1 px-3.5 py-3 text-base text-slate-900 placeholder:text-slate-400 focus:outline-none min-h-[48px]"
                  autoFocus
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || mobileNumber.length !== 10}
              className="w-full py-3 px-4 bg-saffron hover:bg-saffron-600 disabled:opacity-50 disabled:pointer-events-none text-white rounded-lg font-bold text-base transition flex items-center justify-center gap-2 min-h-[48px] shadow-sm"
            >
              {isLoading ? 'Sending OTP...' : t('auth.send_otp')}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-slate-400 font-semibold">{t('auth.or')}</span>
            </div>
          </div>

          {/* Alternate OAuth / Email Login Buttons */}
          <div className="space-y-2.5">
            {/* Google Login Button */}
            <button
              type="button"
              onClick={() => setShowGoogleModal(true)}
              className="w-full py-2.5 px-4 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 rounded-lg font-medium text-sm transition flex items-center justify-center gap-2.5 min-h-[44px]"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
              </svg>
              <span>{t('auth.google')}</span>
            </button>

            {/* Prominent Demo Account Button */}
            <button
              type="button"
              onClick={handleDemoLogin}
              className="w-full py-2.5 px-4 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-success font-bold rounded-lg text-sm transition flex items-center justify-center gap-2 min-h-[44px]"
            >
              <span>✨ {t('auth.demo_btn')} (1-Click Ananya)</span>
            </button>
          </div>

          {/* Privacy & Aadhaar Security Note */}
          <div className="mt-6 p-3 bg-slate-50 rounded-lg flex items-center gap-2 text-xs text-slate-500 border border-slate-100">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{t('auth.aadhaar_note')}</span>
          </div>

          {/* Sign up Link */}
          <div className="mt-6 text-center text-sm">
            <Link to="/signup" className="text-saffron font-bold hover:underline">
              {t('auth.new_here')}
            </Link>
          </div>
        </div>
      </div>

      {/* Google / Email Account Modal */}
      {showGoogleModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => setShowGoogleModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Sign in with Google / Email</h3>
                <p className="text-xs text-slate-500">Sign in using your actual personal account</p>
              </div>
            </div>

            {googleError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-danger font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{googleError}</span>
              </div>
            )}

            <form onSubmit={handleGoogleSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wider">
                  Your Gmail / Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
                  <input
                    type="email"
                    required
                    placeholder="your.name@gmail.com"
                    value={googleEmail}
                    onChange={(e) => setGoogleEmail(e.target.value)}
                    className="w-full pl-9 pr-3.5 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-saffron focus:ring-2 focus:ring-saffron/20"
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wider">
                  Full Name (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Rahul Sharma"
                  value={googleName}
                  onChange={(e) => setGoogleName(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-saffron focus:ring-2 focus:ring-saffron/20"
                />
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg text-sm transition flex items-center justify-center gap-2 shadow-sm"
              >
                <span>Continue to YojanaAgent</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="pt-2 text-center">
                <button
                  type="button"
                  onClick={() => {
                    setGoogleEmail('user.citizen@gmail.com');
                    setGoogleName('Citizen User');
                  }}
                  className="text-xs text-saffron hover:underline font-medium"
                >
                  Fill Sample (user.citizen@gmail.com)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer Links */}
      <footer className="text-center text-xs text-slate-500 py-3">
        <Link to="/privacy" className="hover:underline">
          {t('auth.privacy_link')}
        </Link>
        {' • '}
        <span>Non-governmental independent civic assistant</span>
      </footer>
    </div>
  );
};
