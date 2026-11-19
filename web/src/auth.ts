// Auth session management for YojanaAgent

import { UserSession, UserProfile } from './types';

const AUTH_KEY = 'yojana_agent_auth_session';
const LAST_ACTIVITY_KEY = 'yojana_agent_last_activity';
const RETURN_URL_KEY = 'yojana_agent_return_url';

export const DEMO_USER: UserProfile = {
  id: 'usr_demo_01',
  name: 'Ananya Verma',
  phone: '+91 98765 12345',
  email: 'ananya.verma@example.com',
  language: 'en',
  isVerified: true,
  storageConsent: true,
  reminderConsent: true,
  channelPreferences: {
    email: true,
    telegram: true,
    sms: false,
  },
  sessions: [
    { device: 'Chrome on Windows (Current)', ip: '103.21.244.12', lastActive: 'Just now', current: true },
    { device: 'Safari on iPhone 15', ip: '157.34.120.45', lastActive: 'Yesterday', current: false },
  ],
};

export const auth = {
  getSession(): UserSession | null {
    try {
      const data = localStorage.getItem(AUTH_KEY);
      if (!data) return null;
      return JSON.parse(data) as UserSession;
    } catch {
      return null;
    }
  },

  setSession(session: UserSession): void {
    localStorage.setItem(AUTH_KEY, JSON.stringify(session));
    this.updateActivity();
  },

  clearSession(): void {
    localStorage.removeItem(AUTH_KEY);
    localStorage.removeItem(LAST_ACTIVITY_KEY);
  },

  logout(): void {
    this.clearSession();
  },

  isDemoUser(): boolean {
    const user = this.getCurrentUser();
    return user?.id === DEMO_USER.id;
  },

  login(phone: string, name?: string): UserSession {
    return this.loginWithPhone(phone, name);
  },

  loginWithPhone(phone: string, name?: string): UserSession {
    const cleanDigits = phone.replace(/\D/g, '');
    const formattedPhone = cleanDigits.length === 10 ? `+91 ${cleanDigits.slice(0, 5)} ${cleanDigits.slice(5)}` : phone;
    const userId = 'usr_p_' + cleanDigits;

    const session: UserSession = {
      token: 'phone_tok_' + Date.now(),
      user: {
        id: userId,
        phone: formattedPhone,
        name: name || `Citizen (${formattedPhone})`,
        email: '',
        language: 'en',
        isVerified: true,
        storageConsent: true,
        reminderConsent: false,
        channelPreferences: {
          email: false,
          telegram: false,
          sms: true,
        },
        sessions: [
          { device: 'Current Browser Session', ip: '127.0.0.1', lastActive: 'Just now', current: true },
        ],
      },
    };
    this.setSession(session);
    return session;
  },

  loginWithEmail(email: string, name?: string): UserSession {
    const trimmed = email.trim();
    const derivedName = name?.trim() || trimmed.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    const cleanEmailId = trimmed.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 24);
    const userId = 'usr_e_' + cleanEmailId;

    const session: UserSession = {
      token: 'email_tok_' + Date.now(),
      user: {
        id: userId,
        email: trimmed,
        name: derivedName || 'Google Citizen',
        phone: '',
        language: 'en',
        isVerified: true,
        storageConsent: true,
        reminderConsent: false,
        channelPreferences: {
          email: true,
          telegram: false,
          sms: false,
        },
        sessions: [
          { device: 'Current Browser Session (Google / Email)', ip: '127.0.0.1', lastActive: 'Just now', current: true },
        ],
      },
    };
    this.setSession(session);
    return session;
  },

  isAuthenticated(): boolean {
    const session = this.getSession();
    return !!session && !!session.token;
  },

  getCurrentUser(): UserProfile | null {
    const session = this.getSession();
    return session ? session.user : null;
  },

  updateUser(updates: Partial<UserProfile>): UserProfile | null {
    const session = this.getSession();
    if (!session) return null;
    session.user = { ...session.user, ...updates };
    this.setSession(session);
    return session.user;
  },

  updateActivity(): void {
    localStorage.setItem(LAST_ACTIVITY_KEY, Date.now().toString());
  },

  getLastActivity(): number {
    const ts = localStorage.getItem(LAST_ACTIVITY_KEY);
    return ts ? parseInt(ts, 10) : Date.now();
  },

  setReturnUrl(url: string): void {
    localStorage.setItem(RETURN_URL_KEY, url);
  },

  getReturnUrl(): string {
    const url = localStorage.getItem(RETURN_URL_KEY);
    localStorage.removeItem(RETURN_URL_KEY);
    return url && url !== '/login' && url !== '/verify' ? url : '/';
  },

  loginWithDemo(): UserSession {
    const session: UserSession = {
      token: 'demo_token_' + Date.now(),
      user: { ...DEMO_USER },
    };
    this.setSession(session);
    return session;
  },
};
