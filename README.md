# 🇮🇳 YojanaAgent: Autonomous Government Scheme-Matching Assistant

> *"You give it your situation in Hindi or English, by text, voice, or document photo. It finds every scheme you qualify for, verifies it against official sources, fills your applications, and tracks them until you get the benefit."*

---

## 🌟 LLM-Driven Architecture Overview

YojanaAgent is an **LLM-first, privacy-grounded autonomous welfare assistant** designed for Indian citizens. It replaces rigid hand-coded eligibility tables with grounded generative reasoning powered by Google Gemini (with Anthropic backup), backed by strict verification and privacy guarantees:

1. **LLM-First Decisions & Evidentiary Grounding**: Eligibility, OCR extraction, validity/expiry calculations, cross-document consistency, scheme modifications, and rejection explanations are evaluated through `LLMClient.generate_structured()` against official policy documents in ChromaDB. Every verdict mandates verbatim `evidence_quotes` copied from the official text.
2. **Two-Pass Reviewer Audit**: Every eligibility verdict and validity determination is audited by a second, independent LLM prompt (`ReviewerAuditResult`). If the auditor disagrees or confidence falls below $0.7$, the determination is strictly flagged as `NEEDS_REVIEW` instead of stating assumptions as fact.
3. **Strict Date Arithmetic & Current Date Injection**: Today's date is injected into every prompt involving deadlines, age, or validity, requiring the model to show explicit date calculations in `date_calculation_reasoning`.
4. **Zero Silent Fallbacks**: If no LLM API key is configured or the provider fails, the system surfaces a clear `LLM unavailable` status rather than fabricating results. The deterministic rule engine (`knowledge/rule_engine.py`) is preserved and used only when explicitly enabled via `DECISION_MODE=rules`.
5. **Privacy & Right-to-Erasure**:
   - Citizen documents are Fernet-encrypted under `data/vault/<user_id>/<doc_id>.enc`.
   - All 12-digit Aadhaar numbers are automatically masked (`XXXX-XXXX-1234`) before entering prompts or logs.
   - `DELETE /me/data` permanently purges the user's encrypted vault, saved profile facts, and history.
6. **Human-in-the-Loop Approval Gate**: Outbound citizen alerts and messages are drafted in the citizen's preferred language (Hindi in Devanagari or English), saved as `PENDING_APPROVAL`, and sent *only* upon explicit citizen authorization (`NOTIFY_DRY_RUN=true` by default).

---

## 📂 Project Architecture

```
Yojana-Agent/
├── shared/
│   ├── schemas.py           # Core Pydantic schemas (frozen immutability; 10 schema sections)
│   └── config.py            # Environment settings, paths, and provider parameters
├── brain/                   # Orchestrator & API
│   ├── api.py               # FastAPI REST endpoints scoped by X-User-Id
│   ├── graph.py             # Autonomous LangGraph feedback loop
│   ├── planner.py           # Structured reasoning planner with tool selection
│   ├── asker.py             # Gap-Asker & profile vs. document conflict resolution
│   ├── critic.py            # Hallucination and groundedness auditor
│   ├── tool_registry.py     # Typed tool definitions (vault, notifier, tracker, matching)
│   └── llm_client.py        # Gemini-3.5-flash-lite / Claude client with SQLite caching
├── knowledge/               # Schemes, Vector Store & Policy Monitoring
│   ├── schemes/             # 21 official government scheme JSON definitions
│   ├── llm_matcher.py       # Grounded eligibility matcher with Reviewer audit & explanations
│   ├── matcher.py           # Hybrid matcher dispatching to LLM or rules based on DECISION_MODE
│   ├── semantic_search.py   # ChromaDB dense multilingual embeddings
│   ├── monitor.py           # Official portal scraper, diff summarizer, and APScheduler
│   └── rule_engine.py       # Deterministic rule engine (active when DECISION_MODE=rules)
├── experience/              # Citizen Interfaces & Actions
│   ├── intake/
│   │   ├── vault.py         # Fernet-encrypted document storage (Right-to-Erasure compliant)
│   │   └── doc_extractor.py # Multimodal vision OCR & cross-document consistency auditor
│   ├── dashboard/
│   │   ├── validity_tracker.py # Document expiry reasoning with Reviewer audit
│   │   └── application_tracker.py # SQLite application progress tracker
│   └── actions/
│       ├── notifier.py      # LLM message drafting, deduplication, rate limits, approval gate
│       └── pdf_filler.py    # Official prefilled application PDF generator
├── web/                     # React + TypeScript + Tailwind + shadcn/ui frontend
├── tests/                   # Complete offline unit test suite (35 passing tests)
└── README.md
```

---

## 🏗️ 6-Phase Implementation Breakdown

### Phase 1: Encrypted Document Vault & Vision OCR
- **Multimodal OCR**: `DocumentExtractor.extract_from_image()` uses vision LLM inference to extract document type, holder name, DOB, issue date, validity, income, and last-4 ID digits.
- **Symmetric Encryption**: `DocumentVault` secures documents with Fernet symmetric encryption under `data/vault/<user_id>/<doc_id>.enc`.
- **Scheme Linkage & Consistency**: Matches uploaded documents against scheme `documents_required` and audits cross-document name, DOB, and income discrepancies.
- **Verified by**: `tests/test_phase1_vault.py` (6 tests).

### Phase 2: Document Validity & Expiry Tracking
- **Two-Pass Validity Evaluation**: Injects current date into prompts; requires explicit date calculations in `date_calculation_reasoning`.
- **Auditor Self-Check**: Second-pass Reviewer audits determination; marks `NEEDS_REVIEW` if confidence $< 0.7$ or auditor disagrees.
- **Scheduled Background Alerts**: `DailyValidityScheduler` (APScheduler) runs daily checks for expiring certificates.
- **Mandatory Disclaimer**: Surfaces required legal disclaimer: *"The system detects expiry and provides renewal guidance, but cannot renew documents on your behalf."*
- **Verified by**: `tests/test_phase2_validity.py` (4 tests).

### Phase 3: Official Scheme Monitor & Deadlines
- **Portal Scraper**: Weekly fetch using `requests` + `BeautifulSoup` with timeouts; network failures never count as policy changes.
- **Diff Summaries**: LLM compares portal text with stored baseline and produces `SchemeChangeSummary` with verbatim `evidence_quotes`. Saved strictly as `NEEDS_REVIEW` (never auto-edits scheme definitions).
- **Citizen Re-Evaluation**: Approving a scheme update re-evaluates all saved citizen profiles in SQLite and generates user alerts.
- **Deadline Extraction**: Extracts registration and application cut-off dates into a queryable table.
- **Verified by**: `tests/test_phase3_monitor.py` (3 tests).

### Phase 4: Human-in-the-Loop Notifications & Outbound Drafts
- **AI Drafting & Localization**: `NotificationService` composes outbound messages across email, Telegram, SMS, and in-app in the citizen's language (Hindi or English).
- **Aadhaar Masking**: All 12-digit Aadhaar numbers are masked to `XXXX-XXXX-1234` before prompt submission and on generated output.
- **Approval Guarantee**: Stored as `PENDING_APPROVAL` with the guarantee: *"Nothing is sent without your approval."*
- **Deduplication & Rate Limiting**: 24-hour SHA-256 fingerprint deduplication prevents redundant messages; hourly rate limit restricts dispatches ($\le 10$/hr).
- **Dry-Run Mode**: Defaults to `NOTIFY_DRY_RUN=true` to simulate dispatch safely without sending unsolicited external messages.
- **Verified by**: `tests/test_phase4_notifier.py` (6 tests).

### Phase 5: Smarter Profile & LLM-Driven Matcher
- **Grounded Eligibility Evaluation**: `LLMMatcher` queries ChromaDB for official policy text and requires verbatim `evidence_quotes` with automatic single-retry enforcement.
- **Auditor Verification**: Audits verdict with `ReviewerAuditResult`, setting status to `NEEDS_REVIEW` on discrepancy.
- **Rejection Explanations & Next-Best Schemes**: Generates compassionate, plain-language explanations of disqualifications and suggests top alternative schemes.
- **Profile vs. Document Conflict Resolution**: `GapAsker` detects contradictions between self-reported facts and vault certificates, prioritizing bilingual clarification questions before asking for missing fields.
- **Verified by**: `tests/test_phase5_llm_matcher.py` (6 tests).

### Phase 6: Scoped FastAPI API & Right-to-Erasure
- **X-User-Id Dependency**: All user-specific operations are scoped via `get_current_user_id()`.
- **Vault Routes**: `POST /vault/upload`, `GET /vault/documents`, `GET /vault/health`, `GET /vault/consistency`.
- **Scheme Intelligence**: `GET /schemes/updates`, `GET /schemes/deadlines`, `GET /schemes/{id}/explain-rejection`.
- **Notification Routes**: `GET /drafts`, `POST /drafts/{id}/approve`, `POST /drafts/{id}/discard`.
- **Right to Erasure**: `DELETE /me/data` permanently erases all vault files, profile facts, alerts, and drafts.
- **Verified by**: `tests/test_phase6_api.py` (8 tests).

---

## 🚀 Setup & Execution

### 1. Environment Configuration

Copy the sample environment file and configure your keys:
```bash
cp .env.example .env
```

Key environment variables:
```env
# LLM Providers
GOOGLE_API_KEY="your-google-api-key"
GEMINI_MODEL="gemini-3.5-flash-lite"
ANTHROPIC_API_KEY=""
ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"

# Decision Mode: "llm" (default, LLM-first) or "rules" (deterministic fallback)
DECISION_MODE="llm"

# Privacy & Document Vault
VAULT_KEY=""                       # 32-byte Fernet key (auto-generated if empty)

# Notifications & Approvals
NOTIFY_DRY_RUN="true"              # true = simulate dispatches; false = live SMTP/Telegram
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER=""
SMTP_PASSWORD=""
TELEGRAM_BOT_TOKEN=""
```

### 2. Run the Test Suite

All 35 unit tests are designed to run completely offline without external network dependencies:
```powershell
.\.venv\Scripts\pytest.exe -v
```

Run specific phase test suites:
```powershell
.\.venv\Scripts\pytest.exe tests/test_phase1_vault.py -v
.\.venv\Scripts\pytest.exe tests/test_phase2_validity.py -v
.\.venv\Scripts\pytest.exe tests/test_phase3_monitor.py -v
.\.venv\Scripts\pytest.exe tests/test_phase4_notifier.py -v
.\.venv\Scripts\pytest.exe tests/test_phase5_llm_matcher.py -v
.\.venv\Scripts\pytest.exe tests/test_phase6_api.py -v
```

### 3. Launch FastAPI Backend

```powershell
.\.venv\Scripts\uvicorn.exe brain.api:app --reload --host 127.0.0.1 --port 8000
```
Interactive API documentation will be available at: `http://127.0.0.1:8000/docs`

### 4. Launch React Web Frontend

```powershell
npm run dev --prefix web
```
The React frontend will be available at: `http://127.0.0.1:5173/`
