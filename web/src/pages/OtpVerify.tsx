import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { auth } from '../auth';
import { CheckCircle2, AlertCircle, ArrowLeft, RefreshCw, MessageSquare, Zap } from 'lucide-react';

export const OtpVerify: React.FC = () => {
  const { t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();

  const stateData = location.state as { phone?: string; generatedOtp?: string } | undefined;
  const phone = stateData?.phone || sessionStorage.getItem('yojana_pending_phone') || '+91 98765 12345';

  // Retrieve or generate OTP
  const [activeOtp, setActiveOtp] = useState<string>(() => {
    return (
      stateData?.generatedOtp ||
      sessionStorage.getItem('yojana_active_otp') ||
      Math.floor(100000 + Math.random() * 900000).toString()
    );
  });

  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [resendTimer, setResendTimer] = useState(30);
  const [shake, setShake] = useState(false);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Store active OTP in sessionStorage
  useEffect(() => {
    sessionStorage.setItem('yojana_active_otp', activeOtp);
  }, [activeOtp]);

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

  const verifyCode = (code: string) => {
    setIsVerifying(true);
    setError(null);

    setTimeout(() => {
      setIsVerifying(false);
      // Valid if it matches the generated active OTP OR standard demo code 123456
      if (code === activeOtp || code === '123456') {
        setIsSuccess(true);
        // Login with citizen's specific phone number
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
    }, 500);
  };

  const autoFillOtp = (code: string) => {
    const chars = code.split('').slice(0, 6);
    setDigits(chars);
    verifyCode(code);
  };

  const handleResend = () => {
    const newCode = Math.floor(100000 + Math.random() * 900000).toString();
    setActiveOtp(newCode);
    setResendTimer(30);
    setDigits(['', '', '', '', '', '']);
    setError(null);
    inputRefs.current[0]?.focus();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center p-4">
      <div className="max-w-md w-full bg-white rounded-card shadow-soft-hover border border-slate-200 p-6 sm:p-8">
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-5 font-medium min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{t('otp.change_number')}</span>
        </Link>

        {/* Live Incoming SMS Message Notification Banner */}
        <div className="mb-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/80 rounded-xl shadow-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-saffron" />
              SMS Delivered to {phone}
            </span>
            <span className="text-[10px] text-amber-800 font-semibold bg-amber-100 px-2 py-0.5 rounded-full">
              Just now
            </span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">
            Your YojanaAgent verification OTP is:{' '}
            <strong className="text-base font-mono font-bold text-slate-950 tracking-wider bg-white px-2 py-0.5 rounded border border-amber-200 shadow-2xs">
              {activeOtp}
            </strong>
          </p>
          <div className="mt-2.5 pt-2 border-t border-amber-200/60 flex items-center justify-between">
            <button
              type="button"
              onClick={() => autoFillOtp(activeOtp)}
              className="text-xs font-bold text-saffron hover:text-saffron-700 flex items-center gap-1.5 transition underline py-1"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>One-Tap Auto-fill ({activeOtp})</span>
            </button>
            <span className="text-[11px] text-slate-500">or use 123456</span>
          </div>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-1.5">Verify Mobile</h1>
        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          {t('otp.enter_code')}{' '}
          <span className="font-semibold text-slate-900">{phone}</span>.
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
