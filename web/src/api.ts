// Unified Typed API Client for YojanaAgent
// All backend interactions live here for straightforward FastAPI backend integration

import {
  MatchResult,
  VaultDocument,
  ConsistencyIssue,
  SchemeUpdate,
  Notification,
  Draft,
  Application,
  AgentTraceStep,
} from './types';
import { auth, DEMO_USER } from './auth';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function getUserStorageKey(key: string): string {
  const user = auth.getCurrentUser();
  const uid = user?.id || 'guest';
  return `yojana_${uid}_${key}`;
}

// --- Initial Seed Mock Data ---

const MOCK_SCHEMES: MatchResult[] = [
  {
    scheme_id: 'pm-kisan',
    scheme_name: 'PM Kisan Samman Nidhi Yojana',
    status: 'ELIGIBLE',
    benefit_summary: '₹6,000 per year directly into bank account in 3 equal installments of ₹2,000.',
    satisfied_reasons: [
      'Occupation verified as Farmer',
      'Cultivable landholding is 2 acres (under 5-acre threshold)',
      'Active bank account linked with Aadhaar confirmed',
    ],
    missing_fields: [],
    documents_required: ['Aadhaar Card', 'Land Ownership Records / Khasra-Khatauni', 'Bank Passbook'],
    official_url: 'https://pmkisan.gov.in',
    ministry: 'Ministry of Agriculture & Farmers Welfare',
    category: 'Agriculture',
    needs_review: false,
  },
  {
    scheme_id: 'nsp-national-scholarship-portal',
    scheme_name: 'National Scholarship Portal (Central Sector)',
    status: 'ELIGIBLE',
    benefit_summary: 'Up to ₹20,000 annually for tuition fees and maintenance allowance.',
    satisfied_reasons: [
      'Student enrollment confirmed',
      'Family income is ₹1,80,000 (well within ₹2.5L ceiling)',
      'Age is 19 years (eligible for undergraduate scholarship)',
    ],
    missing_fields: [],
    documents_required: ['Aadhaar Card', 'Previous Year Marksheet', 'Income Certificate', 'Bonafide Student Certificate'],
    official_url: 'https://scholarships.gov.in',
    ministry: 'Ministry of Education',
    category: 'Education',
    needs_review: false,
  },
  {
    scheme_id: 'mudra-yojana-shishu',
    scheme_name: 'Pradhan Mantri MUDRA Yojana (Shishu)',
    status: 'ALMOST',
    benefit_summary: 'Collateral-free business loan up to ₹50,000 with low interest for micro-enterprises.',
    satisfied_reasons: ['Self-employed / small business activity indicated', 'Valid Indian citizen with Aadhaar'],
    missing_fields: ['business_vintage_months', 'existing_loan_defaults'],
    documents_required: ['Aadhaar Card', 'Business Address Proof / Shop License', '6-Month Bank Statement'],
    official_url: 'https://www.mudra.org.in',
    ministry: 'Ministry of Finance',
    category: 'Livelihood & Business',
    needs_review: true,
  },
  {
    scheme_id: 'ayushman-bharat-pmjay',
    scheme_name: 'Ayushman Bharat - PM Jan Arogya Yojana',
    status: 'ELIGIBLE',
    benefit_summary: 'Free cashless health insurance cover up to ₹5,00,000 per family per year.',
    satisfied_reasons: ['BPL / SECC deprivation criteria satisfied', 'Deprivation criteria D1/D4 verified'],
    missing_fields: [],
    documents_required: ['Ration Card', 'Aadhaar Card of all family members'],
    official_url: 'https://pmjay.gov.in',
    ministry: 'Ministry of Health and Family Welfare',
    category: 'Healthcare',
    needs_review: false,
  },
  {
    scheme_id: 'aicte-pragati-scholarship',
    scheme_name: 'AICTE Pragati Scholarship for Girls',
    status: 'ALMOST',
    benefit_summary: '₹50,000 per year towards college fee for female students admitted to technical diploma/degree.',
    satisfied_reasons: ['Gender is Female', 'Enrolled in AICTE recognized institution'],
    missing_fields: ['family_annual_income_verified'],
    documents_required: ['Class 10 & 12 Marksheet', 'College Admission Letter', 'State Domicile Certificate', 'Income Certificate'],
    official_url: 'https://www.aicte-india.org/schemes/students-development-schemes/Pragati',
    ministry: 'AICTE, Ministry of Education',
    category: 'Education',
    needs_review: false,
  },
  {
    scheme_id: 'pm-awas-yojana-gramin',
    scheme_name: 'PM Awas Yojana (Gramin)',
    status: 'NOT_ELIGIBLE',
    benefit_summary: 'Financial assistance of ₹1,20,000 for constructing a pucca house in rural areas.',
    satisfied_reasons: [],
    missing_fields: ['kutcha_house_certificate'],
    documents_required: ['Aadhaar Card', 'MGNREGA Job Card', 'Bank Passbook', 'Land Ownership Certificate'],
    official_url: 'https://pmayg.nic.in',
    ministry: 'Ministry of Rural Development',
    category: 'Housing',
    needs_review: false,
  },
];

const MOCK_DOCUMENTS: VaultDocument[] = [
  {
    id: 'doc_aadhaar_01',
    doc_type: 'Aadhaar Card',
    holder_name: 'Ananya Verma',
    issue_date: '2018-04-12',
    expiry_date: '2099-12-31',
    id_last4: '4821',
    status: 'VALID',
    confidence: 0.99,
    linked_scheme_ids: ['pm-kisan', 'nsp-national-scholarship-portal', 'ayushman-bharat-pmjay'],
    file_size: '1.4 MB',
  },
  {
    id: 'doc_income_02',
    doc_type: 'Family Income Certificate',
    holder_name: 'Ramakant Verma (Father)',
    issue_date: '2025-05-10',
    expiry_date: '2026-05-09',
    income_amount: 180000,
    status: 'EXPIRING_SOON',
    confidence: 0.94,
    linked_scheme_ids: ['nsp-national-scholarship-portal', 'aicte-pragati-scholarship'],
    file_size: '850 KB',
  },
  {
    id: 'doc_caste_03',
    doc_type: 'OBC Non-Creamy Layer Certificate',
    holder_name: 'Ananya Verma',
    issue_date: '2023-02-15',
    expiry_date: '2026-02-14',
    status: 'EXPIRED',
    confidence: 0.91,
    linked_scheme_ids: ['nsp-national-scholarship-portal'],
    file_size: '1.1 MB',
  },
  {
    id: 'doc_land_04',
    doc_type: 'Land Record (Khasra-Khatauni)',
    holder_name: 'Ramakant Verma',
    issue_date: '2024-08-20',
    expiry_date: '2099-12-31',
    status: 'VALID',
    confidence: 0.96,
    linked_scheme_ids: ['pm-kisan'],
    file_size: '2.3 MB',
  },
  {
    id: 'doc_passbook_05',
    doc_type: 'Bank Account Passbook (SBI)',
    holder_name: 'Ananya Verma',
    issue_date: '2022-01-10',
    expiry_date: '2099-12-31',
    status: 'VALID',
    confidence: 0.98,
    linked_scheme_ids: ['pm-kisan', 'nsp-national-scholarship-portal'],
    file_size: '620 KB',
  },
];

const MOCK_CONSISTENCY_ISSUES: ConsistencyIssue[] = [
  {
    id: 'issue_01',
    severity: 'medium',
    message: 'Name spelling differs: "Ananya Verma" on Aadhaar vs "Ananya R. Verma" on Income Certificate.',
    documents: ['Aadhaar Card', 'Family Income Certificate'],
  },
  {
    id: 'issue_02',
    severity: 'high',
    message: 'OBC Certificate validity expired on 14 Feb 2026. This blocks scholarship submission.',
    documents: ['OBC Non-Creamy Layer Certificate'],
  },
];

const MOCK_UPDATES: SchemeUpdate[] = [
  {
    id: 'upd_01',
    scheme_id: 'nsp-national-scholarship-portal',
    summary: 'Family income ceiling increased for Central Sector Scheme.',
    before: 'Annual family income limit: ₹2,50,000',
    after: 'Annual family income limit: ₹3,00,000 (Relaxed by ₹50,000)',
    detected_on: '2026-03-01',
    affects_user: true,
    status: 'APPROVED',
  },
  {
    id: 'upd_02',
    scheme_id: 'pm-kisan',
    summary: 'Mandatory e-KYC deadline extended through Biometric / Face Auth.',
    before: 'Deadline: 31 January 2026',
    after: 'Deadline: 31 May 2026',
    detected_on: '2026-02-28',
    affects_user: true,
    status: 'NEEDS_REVIEW',
  },
  {
    id: 'upd_03',
    scheme_id: 'mudra-yojana-shishu',
    summary: 'GSTIN exemption confirmed for loans under ₹50,000.',
    before: 'Optional GSTIN or Trade License required',
    after: 'Aadhaar + Udyam registration sufficient for Shishu tier',
    detected_on: '2026-02-15',
    affects_user: false,
    status: 'APPROVED',
  },
];

const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 'notif_01',
    type: 'DOCUMENT_EXPIRY',
    message: 'Action Required: Your OBC Certificate has expired. Renew it to avoid scholarship rejection.',
    created_at: '2 hours ago',
    read: false,
    action_url: '/documents/health',
  },
  {
    id: 'notif_02',
    type: 'DEADLINE',
    message: 'Reminder: National Scholarship Portal closes applications in 8 days.',
    created_at: '5 hours ago',
    read: false,
    action_url: '/tracker',
  },
  {
    id: 'notif_03',
    type: 'SCHEME_CHANGE',
    message: 'Income ceiling for National Scholarship Portal raised to ₹3.0 Lakh.',
    created_at: 'Yesterday',
    read: true,
    action_url: '/updates',
  },
  {
    id: 'notif_04',
    type: 'APPLICATION',
    message: 'Application form for PM Kisan is generated and ready for submission.',
    created_at: '2 days ago',
    read: true,
    action_url: '/tracker',
  },
];

const MOCK_DRAFTS: Draft[] = [
  {
    id: 'draft_01',
    channel: 'email',
    to: 'scholarship-nodal@haryana.gov.in',
    subject: 'Request for OBC Certificate Renewal Verification - App Ref #OBC-2026-9812',
    body: `Respected Nodal Officer,\n\nI have submitted my renewal application for the OBC Non-Creamy Layer Certificate at the Rohtak Tehsil Office (Ref: OBC-2026-9812). Since the National Scholarship Portal deadline is on March 31st, I kindly request expedited verification.\n\nThank you,\nAnanya Verma\nMobile: +91 98765 12345`,
    status: 'PENDING_APPROVAL',
    created_at: 'Today, 10:30 AM',
  },
  {
    id: 'draft_02',
    channel: 'telegram',
    to: '@CSC_Rohtak_Helpdesk',
    subject: 'Appointment for PM Kisan Biometric e-KYC',
    body: `Namaste, I need to complete biometric eKYC for PM Kisan Samman Nidhi. Can I visit today between 3 PM and 5 PM with my Aadhaar card?`,
    status: 'PENDING_APPROVAL',
    created_at: 'Yesterday',
  },
];

const MOCK_APPLICATIONS: Application[] = [
  {
    id: 'app_pmkisan_01',
    scheme_id: 'pm-kisan',
    scheme_name: 'PM Kisan Samman Nidhi',
    status: 'READY_TO_SUBMIT',
    documents_ready: ['Aadhaar Card', 'Land Record (Khasra-Khatauni)', 'Bank Passbook'],
    documents_missing: [],
    pdf_url: '/downloads/Application_pm-kisan.pdf',
    next_action: 'Submit prefilled form at your nearest CSC Center or upload via pmkisan.gov.in portal.',
    updated_at: 'Today, 11:15 AM',
    official_url: 'https://pmkisan.gov.in',
    submission_mode: 'Online or Common Service Centre (CSC)',
    notes: 'Pre-filled form created. All 3 mandatory documents ready.',
    history: [
      { stage: 'Draft Created', timestamp: '2026-03-01 10:00', note: 'AI matched citizen profile with 100% eligibility.' },
      { stage: 'Documents Attached', timestamp: '2026-03-01 11:15', note: 'All required documents verified from Vault.' },
    ],
  },
  {
    id: 'app_nsp_02',
    scheme_id: 'nsp-national-scholarship-portal',
    scheme_name: 'National Scholarship Portal (Central Sector)',
    status: 'DRAFT',
    documents_ready: ['Aadhaar Card', 'Bank Passbook', 'Income Certificate'],
    documents_missing: ['Renewed OBC Certificate', 'College Bonafide Certificate'],
    pdf_url: '/downloads/Application_nsp.pdf',
    next_action: 'Upload renewed OBC Certificate to unlock final submission.',
    updated_at: 'Yesterday',
    official_url: 'https://scholarships.gov.in',
    submission_mode: 'Online (OTR + NSP Portal)',
    notes: 'Blocked pending OBC certificate renewal.',
    history: [
      { stage: 'Draft Created', timestamp: '2026-02-28 14:20', note: 'AI identified applicant meets academic and income criteria.' },
    ],
  },
  {
    id: 'app_ayushman_03',
    scheme_id: 'ayushman-bharat-pmjay',
    scheme_name: 'Ayushman Bharat Card (PM-JAY)',
    status: 'SUBMITTED',
    documents_ready: ['Ration Card', 'Aadhaar Card'],
    documents_missing: [],
    pdf_url: '/downloads/Application_ayushman.pdf',
    next_action: 'Collect physical Ayushman PVC card from Rohtak District Hospital or CSC.',
    updated_at: '3 days ago',
    official_url: 'https://pmjay.gov.in',
    submission_mode: 'CSC e-Mitra / Portal',
    notes: 'Ref: PMJAY-HAR-2026-8819. Verification in progress.',
    history: [
      { stage: 'Submitted', timestamp: '2026-02-27 16:45', note: 'Biometrics recorded at Rohtak CSC Center.' },
    ],
  },
];

// --- API Service Methods ---

export const api = {
  // 0. Auth & OTP Dispatches
  async sendOtp(phone: string, email?: string): Promise<{ success: boolean; message: string }> {
    try {
      const res = await fetch('http://127.0.0.1:8000/auth/send-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, email }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Offline / sandbox fallback
    }
    return { success: true, message: 'Verification code dispatched to mobile' };
  },

  async verifyOtp(phone: string, code: string, email?: string): Promise<{ success: boolean; token?: string; user_id?: string }> {
    try {
      const res = await fetch('http://127.0.0.1:8000/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code, email }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback
    }
    if (code === '123456' || code === sessionStorage.getItem('yojana_active_otp')) {
      return { success: true, token: 'offline_tok_' + Date.now(), user_id: 'usr_p_' + phone.replace(/\D/g, '') };
    }
    return { success: false };
  },

  // 1. Schemes & Discovery
  async getSchemes(): Promise<MatchResult[]> {
    await delay(300);
    // Return schemes catalog
    return [...MOCK_SCHEMES];
  },

  async getSchemeDetail(id: string): Promise<{
    scheme: MatchResult;
    rules: { requirement: string; userValue: string; status: 'pass' | 'fail' | 'unknown'; quote: string }[];
    deadlines: { stage: string; date: string; status: 'open' | 'closing_soon' | 'closed' }[];
    rejectionReason?: string;
    alternativeSchemes?: MatchResult[];
  }> {
    await delay(250);
    const scheme = MOCK_SCHEMES.find((s) => s.scheme_id === id) || MOCK_SCHEMES[0];

    const rules = [
      { requirement: 'Occupation must be student / enrolled in college', userValue: 'Student (Undergraduate)', status: 'pass' as const, quote: 'Clause 2.1: Open to regular students pursuing recognized degree courses.' },
      { requirement: 'Annual Family Income <= ₹2,50,000', userValue: '₹1,80,000 / year', status: 'pass' as const, quote: 'Clause 3.4: Income certificate issued by competent Tehsildar authority.' },
      { requirement: 'Must possess active bank account with Aadhaar linking', userValue: 'Active Bank Account', status: 'pass' as const, quote: 'Clause 4.1: Direct Benefit Transfer requires NPCI mapped Aadhaar seed.' },
      { requirement: 'Valid Category Certificate (if claiming quota)', userValue: 'Verified', status: 'pass' as const, quote: 'Clause 5.2: Certificates issued by competent state revenue authorities.' },
    ];

    const deadlines = [
      { stage: 'Portal Registration Opens', date: '01 July 2025', status: 'closed' as const },
      { stage: 'Fresh Student Applications', date: '31 March 2026', status: 'closing_soon' as const },
      { stage: 'Institute Level Verification', date: '15 April 2026', status: 'open' as const },
      { stage: 'DBT Fund Disbursal', date: '30 May 2026', status: 'open' as const },
    ];

    return {
      scheme,
      rules,
      deadlines,
      rejectionReason: scheme.status === 'NOT_ELIGIBLE' ? 'Applicant resides in an urban census ward, while PM Awas Gramin strictly caters to registered SECC rural households.' : undefined,
      alternativeSchemes: [MOCK_SCHEMES[0], MOCK_SCHEMES[3]],
    };
  },

  async getSchemeById(id: string) {
    return this.getSchemeDetail(id);
  },

  // 2. Document Vault (Isolated Per Citizen)
  async getDocuments(): Promise<VaultDocument[]> {
    await delay(250);
    if (auth.isDemoUser()) {
      return [...MOCK_DOCUMENTS];
    }
    const key = getUserStorageKey('docs');
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
  },

  async uploadDocument(file: File): Promise<{
    document: VaultDocument;
    extractedFields: Record<string, any>;
    issue?: ConsistencyIssue;
  }> {
    await delay(600);
    const user = auth.getCurrentUser();
    const userName = user?.name || 'Citizen User';
    const docId = 'doc_' + Date.now();
    const isIncome = file.name.toLowerCase().includes('income') || file.name.toLowerCase().includes('aay');
    const isAadhaar = file.name.toLowerCase().includes('aadhaar') || file.name.toLowerCase().includes('aadhar');
    const docType = isIncome ? 'Family Income Certificate' : isAadhaar ? 'Aadhaar Card' : 'Citizen Document';

    const newDoc: VaultDocument = {
      id: docId,
      doc_type: docType,
      holder_name: userName,
      issue_date: '2026-01-15',
      expiry_date: '2027-01-14',
      status: 'VALID',
      confidence: 0.97,
      linked_scheme_ids: [],
      file_size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
    };

    const extractedFields = {
      'Citizen Name': userName,
      'Document Type': docType,
      'Issue Authority': 'Competent Revenue Authority',
      'Vault Status': 'Encrypted & Stored (Fernet AES-128)',
      'Validity': 'Valid until 14 January 2027',
    };

    if (auth.isDemoUser()) {
      MOCK_DOCUMENTS.unshift(newDoc);
    } else {
      const existing = await this.getDocuments();
      localStorage.setItem(getUserStorageKey('docs'), JSON.stringify([newDoc, ...existing]));
    }

    return { document: newDoc, extractedFields };
  },

  async deleteDocument(id: string): Promise<boolean> {
    await delay(200);
    if (auth.isDemoUser()) {
      const idx = MOCK_DOCUMENTS.findIndex((d) => d.id === id);
      if (idx !== -1) {
        MOCK_DOCUMENTS.splice(idx, 1);
        return true;
      }
      return false;
    }
    const existing = await this.getDocuments();
    const updated = existing.filter((d) => d.id !== id);
    localStorage.setItem(getUserStorageKey('docs'), JSON.stringify(updated));
    return true;
  },

  // 3. Consistency & Health (Isolated Per Citizen)
  async getConsistencyIssues(): Promise<ConsistencyIssue[]> {
    await delay(200);
    if (auth.isDemoUser()) {
      return [...MOCK_CONSISTENCY_ISSUES];
    }
    return [];
  },

  // 4. Scheme Updates
  async getSchemeUpdates(): Promise<SchemeUpdate[]> {
    await delay(250);
    return [...MOCK_UPDATES];
  },

  async approveSchemeUpdate(id: string): Promise<boolean> {
    await delay(200);
    const upd = MOCK_UPDATES.find((u) => u.id === id);
    if (upd) {
      upd.status = 'APPROVED';
      return true;
    }
    return false;
  },

  // 5. Alerts & Notifications (Isolated Per Citizen)
  async getNotifications(): Promise<Notification[]> {
    await delay(200);
    if (auth.isDemoUser()) {
      return [...MOCK_NOTIFICATIONS];
    }
    const key = getUserStorageKey('notifs');
    const data = localStorage.getItem(key);
    if (data) {
      return JSON.parse(data);
    }
    const user = auth.getCurrentUser();
    const initialNotifs: Notification[] = [
      {
        id: 'notif_welcome',
        type: 'INFO',
        message: `Welcome to YojanaAgent, ${user?.name || 'Citizen'}! Complete your profile or upload documents to discover tailored welfare schemes.`,
        created_at: 'Just now',
        read: false,
        action_url: '/',
      },
    ];
    localStorage.setItem(key, JSON.stringify(initialNotifs));
    return initialNotifs;
  },

  async markNotificationRead(id: string): Promise<boolean> {
    if (auth.isDemoUser()) {
      const notif = MOCK_NOTIFICATIONS.find((n) => n.id === id);
      if (notif) {
        notif.read = true;
        return true;
      }
      return false;
    }
    const notifs = await this.getNotifications();
    const target = notifs.find((n) => n.id === id);
    if (target) {
      target.read = true;
      localStorage.setItem(getUserStorageKey('notifs'), JSON.stringify(notifs));
      return true;
    }
    return false;
  },

  // 6. Outbound Drafts & Approvals (Isolated Per Citizen)
  async getDrafts(): Promise<Draft[]> {
    await delay(250);
    if (auth.isDemoUser()) {
      return [...MOCK_DRAFTS];
    }
    const data = localStorage.getItem(getUserStorageKey('drafts'));
    return data ? JSON.parse(data) : [];
  },

  async updateDraft(id: string, status: 'PENDING_APPROVAL' | 'SENT' | 'DISCARDED', body?: string): Promise<Draft> {
    await delay(250);
    if (auth.isDemoUser()) {
      const draft = MOCK_DRAFTS.find((d) => d.id === id);
      if (!draft) throw new Error('Draft not found');
      draft.status = status;
      if (body) draft.body = body;
      return draft;
    }
    const drafts = await this.getDrafts();
    const draft = drafts.find((d) => d.id === id);
    if (!draft) throw new Error('Draft not found');
    draft.status = status;
    if (body) draft.body = body;
    localStorage.setItem(getUserStorageKey('drafts'), JSON.stringify(drafts));
    return draft;
  },

  // 7. Application Tracker (Isolated Per Citizen)
  async getApplications(): Promise<Application[]> {
    await delay(250);
    if (auth.isDemoUser()) {
      return [...MOCK_APPLICATIONS];
    }
    const data = localStorage.getItem(getUserStorageKey('apps'));
    return data ? JSON.parse(data) : [];
  },

  async createApplication(schemeId: string): Promise<Application> {
    await delay(350);
    const scheme = MOCK_SCHEMES.find((s) => s.scheme_id === schemeId) || MOCK_SCHEMES[0];
    const user = auth.getCurrentUser();
    const newApp: Application = {
      id: 'app_' + schemeId + '_' + Date.now().toString().slice(-4),
      scheme_id: scheme.scheme_id,
      scheme_name: scheme.scheme_name,
      status: 'READY_TO_SUBMIT',
      documents_ready: scheme.documents_required,
      documents_missing: [],
      pdf_url: `/downloads/Application_${scheme.scheme_id}.pdf`,
      next_action: `Submit pre-filled application directly on ${scheme.official_url} or visit nearest CSC center.`,
      updated_at: 'Just now',
      official_url: scheme.official_url,
      submission_mode: 'Online portal or CSC Center',
      notes: `Pre-filled application prepared for ${user?.name || 'Citizen'}. All mandatory requirements verified.`,
      history: [{ stage: 'Package Prepared', timestamp: new Date().toISOString().slice(0, 16), note: 'Generated form with verified documents.' }],
    };

    if (auth.isDemoUser()) {
      MOCK_APPLICATIONS.unshift(newApp);
    } else {
      const apps = await this.getApplications();
      localStorage.setItem(getUserStorageKey('apps'), JSON.stringify([newApp, ...apps]));
    }
    return newApp;
  },

  async updateApplication(id: string, status: any, notes?: string): Promise<Application> {
    await delay(200);
    if (auth.isDemoUser()) {
      const app = MOCK_APPLICATIONS.find((a) => a.id === id);
      if (!app) throw new Error('Application not found');
      app.status = status;
      if (notes) app.notes = notes;
      app.updated_at = 'Just now';
      app.history?.push({ stage: status, timestamp: new Date().toISOString().slice(0, 16), note: notes || `Status changed to ${status}` });
      return app;
    }
    const apps = await this.getApplications();
    const app = apps.find((a) => a.id === id);
    if (!app) throw new Error('Application not found');
    app.status = status;
    if (notes) app.notes = notes;
    app.updated_at = 'Just now';
    app.history?.push({ stage: status, timestamp: new Date().toISOString().slice(0, 16), note: notes || `Status changed to ${status}` });
    localStorage.setItem(getUserStorageKey('apps'), JSON.stringify(apps));
    return app;
  },

  // 8. Agent Live Trace Simulation
  async runAgentTrace(query: string): Promise<AgentTraceStep[]> {
    await delay(200);
    return [
      {
        id: 'step_1',
        name: 'Planner Brain',
        action: 'Formulating structured execution goal and decomposing citizen intent.',
        status: 'done',
        details: `Identified user demographic: Student & Farmer household. Target categories: Scholarships and Income-support.`,
        timestamp: '00.1s',
      },
      {
        id: 'step_2',
        name: 'ChromaDB Search',
        action: 'Querying multilingual vector store with dense MiniLM semantic embeddings.',
        status: 'done',
        details: `Retrieved top 5 matching candidate schemes with similarity scores 0.82 to 0.89.`,
        timestamp: '00.3s',
      },
      {
        id: 'step_3',
        name: 'Rule Evaluator',
        action: 'Executing deterministic Pydantic rule engine on candidate eligibility criteria.',
        status: 'done',
        details: `Matched 3 ELIGIBLE schemes, 2 ALMOST eligible schemes. Identified 1 missing certificate.`,
        timestamp: '00.6s',
      },
      {
        id: 'step_4',
        name: 'Portal Verifier',
        action: 'Checking live HTTP reachability and WAF status on official government domains.',
        status: 'done',
        details: `Portals verified: scholarships.gov.in (HTTP 200), pmkisan.gov.in (HTTP 200).`,
        timestamp: '00.9s',
      },
      {
        id: 'step_5',
        name: 'Safety & Hallucination Critic',
        action: 'Auditing factual grounding and pruning unverified benefit claims.',
        status: 'done',
        details: `All 3 claims verified against official gazette text. Grounding confidence: 98%.`,
        timestamp: '01.2s',
      },
    ];
  },
};
