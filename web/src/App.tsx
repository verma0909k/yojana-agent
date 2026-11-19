import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './context/LanguageContext';
import { ProtectedLayout } from './components/common/ProtectedRoute';

// Pages
import { Login } from './pages/Login';
import { OtpVerify } from './pages/OtpVerify';
import { Signup } from './pages/Signup';
import { Home } from './pages/Home';
import { AgentTrace } from './pages/AgentTrace';
import { Schemes } from './pages/Schemes';
import { SchemeDetail } from './pages/SchemeDetail';
import { Documents } from './pages/Documents';
import { DocumentHealth } from './pages/DocumentHealth';
import { Updates } from './pages/Updates';
import { Alerts } from './pages/Alerts';
import { Tracker } from './pages/Tracker';
import { Account } from './pages/Account';
import { Privacy } from './pages/Privacy';

export const App: React.FC = () => {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/verify" element={<OtpVerify />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected Routes inside App Shell Layout */}
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/trace" element={<AgentTrace />} />
            <Route path="/schemes" element={<Schemes />} />
            <Route path="/schemes/:id" element={<SchemeDetail />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/documents/health" element={<DocumentHealth />} />
            <Route path="/updates" element={<Updates />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/tracker" element={<Tracker />} />
            <Route path="/account" element={<Account />} />
            <Route path="/privacy" element={<Privacy />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  );
};

export default App;
