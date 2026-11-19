import React from 'react';
import { NavLink } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { Home, Compass, FileText, Bell, ClipboardCheck, Sparkles, Shield, User } from 'lucide-react';

export const Navigation: React.FC = () => {
  const { t } = useLanguage();

  const navItems = [
    { to: '/', label: t('nav.home'), icon: Home },
    { to: '/schemes', label: t('nav.schemes'), icon: Compass },
    { to: '/documents', label: t('nav.documents'), icon: FileText },
    { to: '/alerts', label: t('nav.alerts'), icon: Bell, badge: 2 },
    { to: '/tracker', label: t('nav.tracker'), icon: ClipboardCheck },
  ];

  const secondaryItems = [
    { to: '/updates', label: t('nav.updates'), icon: Sparkles },
    { to: '/account', label: t('nav.account'), icon: User },
    { to: '/privacy', label: t('nav.privacy'), icon: Shield },
  ];

  return (
    <>
      {/* Desktop Sidebar (hidden on mobile) */}
      <aside className="hidden md:flex flex-col w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-65px)] p-4 sticky top-[65px] shrink-0">
        <div className="space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Main Navigation
          </p>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-3 rounded-card text-[15px] font-semibold transition min-h-[44px] ${
                    isActive
                      ? 'bg-saffron-50 text-saffron-900 border-l-4 border-saffron shadow-sm'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5 shrink-0" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="w-5 h-5 bg-saffron text-white text-[11px] font-bold rounded-full flex items-center justify-center">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>

        <div className="mt-8 pt-6 border-t border-slate-100 space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            System & Security
          </p>
          {secondaryItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-card text-sm font-medium transition min-h-[44px] ${
                    isActive
                      ? 'bg-slate-100 text-slate-900 font-semibold'
                      : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'
                  }`
                }
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Official Portal Assurance Card in Desktop Sidebar */}
        <div className="mt-auto pt-6">
          <div className="bg-slate-50 border border-slate-200 rounded-card p-3.5 text-xs text-slate-600">
            <p className="font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
              🛡️ Evidentiary Grounding
            </p>
            <p className="leading-relaxed text-slate-500">
              Schemes and eligibility criteria are matched against verified Gazette rules and official ministry portals.
            </p>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Tab Bar (hidden on desktop) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/98 backdrop-blur border-t border-slate-200 px-2 py-1 shadow-lg">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex flex-col items-center justify-center py-1.5 px-2 rounded-lg relative min-h-[48px] min-w-[56px] transition ${
                    isActive ? 'text-saffron font-bold' : 'text-slate-500 hover:text-slate-800'
                  }`
                }
              >
                <div className="relative">
                  <Icon className="w-5 h-5 mb-0.5" />
                  {item.badge && (
                    <span className="absolute -top-1 -right-2 w-4 h-4 bg-saffron text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                      {item.badge}
                    </span>
                  )}
                </div>
                <span className="text-[11px] leading-tight tracking-tight">{item.label}</span>
              </NavLink>
            );
          })}
        </div>
      </nav>
    </>
  );
};
