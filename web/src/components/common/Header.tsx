import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { auth } from '../../auth';
import { Globe, User, Shield, LogOut, ChevronDown, Check } from 'lucide-react';

export const Header: React.FC = () => {
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const user = auth.getCurrentUser();

  const userMenuRef = useRef<HTMLDivElement>(null);
  const langMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
      if (langMenuRef.current && !langMenuRef.current.contains(e.target as Node)) {
        setLangMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    auth.clearSession();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-sm border-b border-slate-200 px-4 md:px-6 py-3 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-2.5 min-h-[44px]">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-saffron to-amber-500 flex items-center justify-center text-white font-bold shadow-sm text-lg">
            य
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-slate-900 text-lg leading-tight tracking-tight flex items-center gap-1.5">
              YojanaAgent <span className="text-[10px] bg-saffron-100 text-saffron-800 px-1.5 py-0.5 rounded-full font-semibold">AI</span>
            </span>
            <span className="text-[11px] text-slate-500 font-medium hidden sm:inline">
              {t('app.tagline')}
            </span>
          </div>
        </Link>

        {/* Right Action Icons: Language Toggle & User Menu */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Always Visible Language Switcher */}
          <div className="relative" ref={langMenuRef}>
            <button
              onClick={() => setLangMenuOpen(!langMenuOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-sm font-semibold transition border border-slate-200 min-h-[44px] focus:outline-none focus:ring-2 focus:ring-saffron"
              aria-label="Toggle language"
            >
              <Globe className="w-4 h-4 text-saffron" />
              <span>{language === 'en' ? 'English' : 'हिंदी'}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            </button>

            {langMenuOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-white rounded-xl shadow-soft-hover border border-slate-200 py-1.5 z-40">
                <button
                  onClick={() => {
                    setLanguage('en');
                    setLangMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 text-sm text-left font-medium min-h-[44px] ${
                    language === 'en' ? 'text-saffron font-bold bg-saffron-50' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span>English</span>
                  {language === 'en' && <Check className="w-4 h-4 text-saffron" />}
                </button>
                <button
                  onClick={() => {
                    setLanguage('hi');
                    setLangMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 text-sm text-left font-medium min-h-[44px] ${
                    language === 'hi' ? 'text-saffron font-bold bg-saffron-50' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span>हिंदी (Hindi)</span>
                  {language === 'hi' && <Check className="w-4 h-4 text-saffron" />}
                </button>
              </div>
            )}
          </div>

          {/* User Profile Menu */}
          {user ? (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 pl-2 pr-1.5 py-1.5 hover:bg-slate-100 rounded-lg transition min-h-[44px] focus:outline-none focus:ring-2 focus:ring-saffron"
              >
                <div className="w-8 h-8 rounded-full bg-saffron-100 text-saffron-800 flex items-center justify-center font-bold text-sm border border-saffron-200">
                  {user.name.charAt(0)}
                </div>
                <span className="text-sm font-semibold text-slate-800 hidden md:inline max-w-[120px] truncate">
                  {user.name}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-soft-hover border border-slate-200 py-1.5 z-40">
                  <div className="px-4 py-2.5 border-b border-slate-100">
                    <p className="text-sm font-semibold text-slate-900 truncate">{user.name}</p>
                    <p className="text-xs text-slate-500 truncate">{user.phone}</p>
                  </div>

                  <Link
                    to="/account"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 font-medium min-h-[44px]"
                  >
                    <User className="w-4 h-4 text-slate-500" />
                    <span>{t('nav.account')}</span>
                  </Link>

                  <Link
                    to="/privacy"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 font-medium min-h-[44px]"
                  >
                    <Shield className="w-4 h-4 text-slate-500" />
                    <span>{t('nav.privacy')}</span>
                  </Link>

                  <div className="border-t border-slate-100 my-1" />

                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 text-left font-medium min-h-[44px]"
                  >
                    <LogOut className="w-4 h-4 text-red-500" />
                    <span>{t('nav.logout')}</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              to="/login"
              className="px-4 py-2 bg-saffron text-white rounded-lg text-sm font-semibold hover:bg-saffron-600 transition min-h-[44px] flex items-center"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
