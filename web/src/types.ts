// Comprehensive types for YojanaAgent Web App

export type SchemeStatus = 'ELIGIBLE' | 'ALMOST' | 'NOT_ELIGIBLE';

export interface MatchResult {
  scheme_id: string;
  scheme_name: string;
  status: SchemeStatus;
  benefit_summary: string;
  satisfied_reasons: string[];
  missing_fields: string[];
  documents_required: string[];
  official_url: string;
  ministry?: string;
  category?: string;
  needs_review?: boolean;
}

export type DocumentValidity = 'VALID' | 'EXPIRING_SOON' | 'EXPIRED';

export interface VaultDocument {
  id: string;
  doc_type: string;
  holder_name: string;
  issue_date: string;
  expiry_date: string;
  income_amount?: number;
  id_last4?: string;
  status: DocumentValidity;
  confidence: number;
  linked_scheme_ids: string[];
  file_size?: string;
  preview_url?: string;
}

export interface ConsistencyIssue {
  id: string;
  severity: 'high' | 'medium' | 'low';
  message: string;
  documents: string[];
}

export interface SchemeUpdate {
  id: string;
  scheme_id: string;
  summary: string;
  before: string;
  after: string;
  detected_on: string;
  affects_user: boolean;
  status: 'NEEDS_REVIEW' | 'APPROVED';
}

export type NotificationType = 'DOCUMENT_EXPIRY' | 'DEADLINE' | 'SCHEME_CHANGE' | 'APPLICATION' | 'INFO';

export interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  created_at: string;
  read: boolean;
  action_url?: string;
}

export type DraftStatus = 'PENDING_APPROVAL' | 'SENT' | 'DISCARDED';

export interface Draft {
  id: string;
  channel: 'email' | 'telegram' | 'sms';
  to: string;
  subject: string;
  body: string;
  status: DraftStatus;
  created_at?: string;
}

export type ApplicationStatus = 'DRAFT' | 'READY_TO_SUBMIT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED';

export interface Application {
  id: string;
  scheme_id: string;
  scheme_name: string;
  status: ApplicationStatus;
  documents_ready: string[];
  documents_missing: string[];
  pdf_url?: string;
  next_action: string;
  updated_at?: string;
  notes?: string;
  submission_mode?: string;
  official_url?: string;
  history?: { stage: string; timestamp: string; note: string }[];
}

export interface ProfileFact {
  field: string;
  label: string;
  value: string | number | boolean;
  confidence: number;
  source: 'document' | 'self-reported';
}

export interface AgentTraceStep {
  id: string;
  name: string;
  action: string;
  status: 'running' | 'done' | 'warning' | 'waiting';
  details?: string;
  timestamp?: string;
}

export interface UserSessionDevice {
  device: string;
  ip: string;
  lastActive: string;
  current: boolean;
}

export interface UserProfile {
  id: string;
  name: string;
  phone: string;
  email: string;
  language: 'en' | 'hi';
  isVerified: boolean;
  storageConsent: boolean;
  reminderConsent: boolean;
  channelPreferences: {
    email: boolean;
    telegram: boolean;
    sms: boolean;
  };
  sessions: UserSessionDevice[];
}

export interface UserSession {
  token: string;
  user: UserProfile;
}

export interface ExtractedFact {
  id: string;
  field: string;
  value: string;
  confidence: number;
  source: 'from document' | 'self-reported';
}
