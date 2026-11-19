import React from 'react';
import { Navigate, useLocation, Outlet } from 'react-router-dom';
import { auth } from '../../auth';
import { Header } from './Header';
import { Navigation } from './Navigation';
import { SessionManager } from './SessionManager';

export const ProtectedLayout: React.FC = () => {
  const location = useLocation();
  const isAuthenticated = auth.isAuthenticated();

  if (!isAuthenticated) {
    // Save current target path to return after successful login
    auth.setReturnUrl(location.pathname + location.search);
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      <Header />
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        <Navigation />
        <main className="flex-1 p-4 md:p-8 pb-24 md:pb-12 max-w-5xl w-full">
          <Outlet />
        </main>
      </div>
      <SessionManager />
    </div>
  );
};
