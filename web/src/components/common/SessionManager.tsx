import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../auth';
import { AlertTriangle, Clock } from 'lucide-react';

export const SessionManager: React.FC = () => {
  const navigate = useNavigate();
  const [showInactivityWarning, setShowInactivityWarning] = useState(false);
  const [showExpiredModal, setShowExpiredModal] = useState(false);
  const [countdown, setCountdown] = useState(60);

  // 15 minutes of inactivity = 15 * 60 * 1000 ms
  const INACTIVITY_LIMIT_MS = 15 * 60 * 1000;
  // Warning triggers 1 minute before expiry
  const WARNING_TRIGGER_MS = 14 * 60 * 1000;

  useEffect(() => {
    // Record user activity on clicks / key presses
    const handleActivity = () => {
      auth.updateActivity();
      if (showInactivityWarning) {
        setShowInactivityWarning(false);
      }
    };

    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('touchstart', handleActivity);

    // Periodic check every 10 seconds
    const interval = setInterval(() => {
      if (!auth.isAuthenticated()) return;

      const elapsed = Date.now() - auth.getLastActivity();

      if (elapsed >= INACTIVITY_LIMIT_MS) {
        setShowInactivityWarning(false);
        setShowExpiredModal(true);
        auth.clearSession();
      } else if (elapsed >= WARNING_TRIGGER_MS && !showInactivityWarning) {
        setShowInactivityWarning(true);
        setCountdown(Math.ceil((INACTIVITY_LIMIT_MS - elapsed) / 1000));
      }
    }, 10000);

    return () => {
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('touchstart', handleActivity);
      clearInterval(interval);
    };
  }, [showInactivityWarning]);

  const handleStayLoggedIn = () => {
    auth.updateActivity();
    setShowInactivityWarning(false);
  };

  const handleReLogin = () => {
    setShowExpiredModal(false);
    navigate('/login');
  };

  return (
    <>
      {/* Inactivity Warning Dialog */}
      {showInactivityWarning && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-card max-w-md w-full p-6 shadow-soft-hover border border-slate-200">
            <div className="flex items-center gap-3 text-warning mb-3">
              <Clock className="w-6 h-6 shrink-0" />
              <h3 className="text-lg font-bold text-slate-900">Are you still there?</h3>
            </div>
            <p className="text-slate-600 text-sm mb-6 leading-relaxed">
              For your privacy and security, your YojanaAgent session will expire in{' '}
              <span className="font-bold text-slate-900">{countdown} seconds</span> due to inactivity.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={handleStayLoggedIn}
                className="w-full py-2.5 px-4 bg-saffron hover:bg-saffron-600 text-white rounded-lg font-semibold text-sm transition min-h-[44px]"
              >
                Stay Logged In
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session Expired Modal */}
      {showExpiredModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-card max-w-md w-full p-6 shadow-soft-hover border border-slate-200 text-center">
            <div className="w-12 h-12 rounded-full bg-red-100 text-danger flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Session Expired</h3>
            <p className="text-slate-600 text-sm mb-6 leading-relaxed">
              Your session has timed out. Please log in again to continue accessing your documents and applications.
            </p>
            <button
              onClick={handleReLogin}
              className="w-full py-2.5 px-4 bg-saffron hover:bg-saffron-600 text-white rounded-lg font-semibold text-sm transition min-h-[44px]"
            >
              Log in again
            </button>
          </div>
        </div>
      )}
    </>
  );
};
