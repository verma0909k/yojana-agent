# 🇮🇳 YojanaAgent: Autonomous Government Scheme-Matching Assistant

> **Hackathon Project | Track A - Problem A4**  
> *"You give it your situation in Hindi or English, by text, voice, or document photo. It finds every scheme you qualify for, verifies it against official sources, fills your applications, and tracks them until you get the benefit."*

---

## 🌟 Why YojanaAgent is Truly Agentic (Not a Chatbot)
1. **Deterministic Python Rule Engine**: Eligibility is computed entirely via strict Python logic (`knowledge/rule_engine.py`). The LLM never hallucinates eligibility.
2. **Autonomous Multi-Agent LangGraph Loop**: Planner, Matcher, Gap-Asker, Verifier, Critic, and Action agents running in a closed feedback loop.
3. **Information-Gain Questioning**: Instead of endless forms, the Gap-Asker asks only the single highest-leverage question that unlocks the most schemes.
4. **Trust & Verification Layer**: Validates official government portal reachability and cross-checks profile documents for contradictions.
5. **Direct Action Layer**: Generates pre-filled application PDFs, calendar reminders (`.ics`), and Common Service Center (CSC) office guidance.
6. **Live Agent Trace Panel**: Full transparent UI panel displaying each agent's internal thoughts, actions, and decisions.

---

## 📂 Project Architecture

```
Yojana-Agent/
├── shared/                  # Core contracts and config
│   ├── schemas.py           # CitizenProfile, MatchResult, AgentState, Scheme
│   └── config.py            # env vars, paths, model names
├── brain/                   # PERSON A: Orchestration & Decision
│   ├── graph.py             # LangGraph StateGraph loop
│   ├── planner.py           # Autonomous step controller
│   ├── asker.py             # Information-gain gap questioner
│   ├── critic.py            # Hallucination and groundedness auditor
│   ├── llm_client.py        # Gemini/Claude unified client with local fallback
│   ├── trace.py             # Chronological trace logger
│   └── api.py               # FastAPI backend endpoints
├── knowledge/               # PERSON B: Schemes & Eligibility
│   ├── schemes/             # 20 real official government scheme JSON definitions
│   ├── rule_engine.py       # Deterministic ELIGIBLE / ALMOST / NOT_ELIGIBLE engine
│   ├── matcher.py           # Retrieval + rule engine runner
│   ├── retriever.py         # Semantic & keyword candidate filter
│   ├── verifier.py          # Portal status & document cross-checks
│   └── monitor.py           # Memory store (SQLite) & proactive alerts
├── experience/              # PERSON C: UI & User Interaction
│   ├── app.py               # Streamlit UI with Live Agent Trace Panel
│   ├── intake/              # Document OCR, Edge-TTS/gTTS voice, Hinglish parser
│   ├── actions/             # PDF application filler, .ics reminders, CSC guidance
│   └── personas/            # One-click hackathon demo personas (Farmer, Student, etc.)
├── tests/                   # Full test suite covering all modules
└── README.md
```

---

## 🚀 Quickstart

### 1. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run Test Suite
```powershell
pytest
```

### 3. Launch Streamlit UI
```powershell
streamlit run experience\app.py
```

### 4. (Optional) Run FastAPI Backend
```powershell
uvicorn brain.api:app --reload
```
