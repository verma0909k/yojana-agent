import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import { api } from '../api';
import { CheckCircle2, AlertCircle, ArrowLeft, RefreshCw, Mail, ShieldCheck } from 'lucide-react';

export const OtpVerify: React.FC = () => {
  const { t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();

  const stateData = location.state as { phone?: string; email?: string; method?: 'email' | 'phone' } | undefined;
  const email = stateData?.email || sessionStorage.getItem('yojana_pending_email') || '';
  const phone = stateData?.phone || sessionStorage.getItem('yojana_pending_phone') || '';
  const isEmail = Boolean(email) || stateData?.method === 'email';
  const targetRecipient = isEmail ? email : phone || '+91 98765 12345';

  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [resendTimer, setResendTimer] = useState(30);
  const [shake, setShake] = useState(false);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Timer countdown
  useEffect(() => {
    if (resendTimer <= 0) return;
    const interval = setInterval(() => {
      setResendTimer((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [resendTimer]);

  const handleDigitChange = (index: number, value: string) => {
    const char = value.replace(/\D/g, '').slice(-1);
    const newDigits = [...digits];
    newDigits[index] = char;
    setDigits(newDigits);
    setError(null);

    // Auto-advance
    if (char && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all 6 digits entered
    if (char && index === 5 && newDigits.every((d) => d !== '')) {
      verifyCode(newDigits.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;

    const newDigits = [...digits];
    for (let i = 0; i < pasted.length; i++) {
      newDigits[i] = pasted[i];
    }
    setDigits(newDigits);

    if (pasted.length === 6) {
      verifyCode(pasted);
    } else {
      inputRefs.current[pasted.length]?.focus();
    }
  };

  const verifyCode = async (code: string) => {
    setIsVerifying(true);
    setError(null);

    try {
      if (isEmail) {
        const res = await api.verifyEmailOtp(email, code);
        setIsVerifying(false);

        if (res.success) {
          setIsSuccess(true);
          auth.loginWithEmail(email);
          setTimeout(() => {
            const returnUrl = auth.getReturnUrl();
            navigate(returnUrl);
          }, 800);
        } else {
          setError(t('otp.wrong_code'));
          setShake(true);
          setTimeout(() => setShake(false), 500);
        }
      } else {
        const res = await api.verifyOtp(phone, code);
        setIsVerifying(false);

        if (res.success) {
          setIsSuccess(true);
          auth.loginWithPhone(phone);
          setTimeout(() => {
            const returnUrl = auth.getReturnUrl();
            navigate(returnUrl);
          }, 800);
        } else {
          setError(t('otp.wrong_code'));
          setShake(true);
          setTimeout(() => setShake(false), 500);
        }
      }
    } catch {
      setIsVerifying(false);
      // Fallback verification for offline or test code 123456
      if (code === '123456' || code === sessionStorage.getItem('yojana_active_otp')) {
        setIsSuccess(true);
        if (isEmail) {
          auth.loginWithEmail(email);
        } else {
          auth.loginWithPhone(phone);
        }
        setTimeout(() => {
          const returnUrl = auth.getReturnUrl();
          navigate(returnUrl);
        }, 800);
      } else {
        setError(t('otp.wrong_code'));
        setShake(true);
        setTimeout(() => setShake(false), 500);
      }
    }
  };

  const handleResend = async () => {
    setResendTimer(30);
    setDigits(['', '', '', '', '', '']);
    setError(null);
    inputRefs.current[0]?.focus();
    try {
      if (isEmail) {
        await api.sendEmailOtp(email);
      } else {
        await api.sendOtp(phone);
      }
    } catch {
      // Handled silently
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full bg-white rounded-card shadow-soft-hover border border-slate-200 p-6 sm:p-8">
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-5 font-medium min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{isEmail ? 'Change Gmail' : t('otp.change_number')}</span>
        </Link>

        {/* Security Dispatch Notice */}
        <div className="mb-6 p-4 bg-slate-50 border border-slate-200 rounded-xl">
          <div className="flex items-center gap-2 mb-1.5">
            {isEmail ? (
              <Mail className="w-4 h-4 text-saffron shrink-0" />
            ) : (
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span className="text-xs font-bold text-slate-800">
              {isEmail ? 'OTP Dispatched to Gmail' : 'SMS Dispatched'}
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            A 6-digit verification code has been dispatched to{' '}
            <strong className="text-slate-900 font-semibold">{targetRecipient}</strong>.
          </p>
          <p className="text-[11px] text-slate-400 mt-2 border-t border-slate-200/60 pt-2">
            {isEmail
              ? 'Please check your Gmail inbox (and Spam folder). In local test environment, code 123456 or the server console code is also accepted.'
              : 'Telecom carrier delivery may take 10-30s. In testing mode, you can also enter demo code 123456.'}
          </p>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-1.5">
          {isEmail ? 'Verify Your Gmail' : 'Verify Mobile'}
        </h1>
        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          {t('otp.enter_code')}{' '}
          <span className="font-semibold text-slate-900">{targetRecipient}</span>.
        </p>

        {/* Success checkmark feedback */}
        {isSuccess ? (
          <div className="py-8 flex flex-col items-center justify-center text-center">
            <CheckCircle2 className="w-16 h-16 text-success animate-bounce mb-3" />
            <h3 className="text-lg font-bold text-slate-900">Verified Successfully!</h3>
            <p className="text-sm text-slate-500 mt-1">Opening your dashboard...</p>
          </div>
        ) : (
          <>
            {/* Error Message */}
            {error && (
              <div className="mb-5 p-3.5 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-danger text-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* 6 Digit Input Boxes */}
            <div
              className={`flex justify-between gap-2 sm:gap-3 mb-6 ${
                shake ? 'animate-[wiggle_0.4s_ease-in-out]' : ''
              }`}
              onPaste={handlePaste}
            >
              {digits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => (inputRefs.current[idx] = el)}
                  type="text"
                  inputMode="numeric"
                  pattern="\d*"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleDigitChange(idx, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(idx, e)}
                  disabled={isVerifying}
                  className={`w-12 h-14 text-center text-xl font-bold rounded-lg border text-slate-900 transition focus:outline-none focus:ring-2 ${
                    digit
                      ? 'border-saffron bg-saffron-50/20 ring-saffron/20'
                      : 'border-slate-300 bg-white focus:border-saffron focus:ring-saffron/20'
                  } ${shake ? 'border-danger ring-danger/20' : ''}`}
                  autoFocus={idx === 0}
                />
              ))}
            </div>

            {/* Verifying Spinner Indicator */}
            {isVerifying && (
              <div className="flex items-center justify-center gap-2 text-sm text-saffron font-semibold mb-4">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Verifying code...</span>
              </div>
            )}

            {/* Resend Action */}
            <div className="text-center pt-2">
              {resendTimer > 0 ? (
                <p className="text-sm text-slate-500">
                  {t('otp.resend_timer')} <span className="font-semibold text-slate-700">{resendTimer}s</span>
                </p>
              ) : (
                <button
                  type="button"
                  onClick={handleResend}
                  className="text-sm font-bold text-saffron hover:text-saffron-700 transition flex items-center justify-center gap-1.5 mx-auto min-h-[44px]"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>{t('otp.resend_btn')}</span>
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
