"""Streamlit UI for YojanaAgent featuring Live Agent Trace Panel, Multimodal Intake & Action Downloads."""

import sys
import tempfile
from pathlib import Path

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from brain.graph import build_graph
from experience.actions.calendar_reminders import create_scheme_reminder_ics
from experience.actions.office_guidance import get_csc_office_guidance
from experience.actions.pdf_filler import generate_application_pdf
from experience.intake.hinglish import NaturalLanguageIntake
from experience.intake.ocr import DocumentOCR
from experience.intake.voice import text_to_speech
from experience.personas.demo_profiles import DEMO_PERSONAS
from knowledge.monitor import MemoryStore
from shared.schemas import AgentState, CitizenProfile, EligibilityStatus, Source

st.set_page_config(
    page_title="YojanaAgent - Autonomous Scheme Matcher",
    page_icon="🇮🇳",
    layout="wide",
)

# Initialize persistent SQLite memory store
memory = MemoryStore()

# Header
st.title("🇮🇳 YojanaAgent: Autonomous Government Scheme-Matching Assistant")
st.caption("Tell us your situation in Hindi, Hinglish, or English. We find, verify, and fill your schemes autonomously.")

# Initialize session state for citizen profile
if "profile" not in st.session_state:
    saved = memory.get_profile("active_session")
    st.session_state.profile = saved if saved else CitizenProfile()

# Sidebar: One-Click Demo Personas & Inputs
with st.sidebar:
    st.header("⚡ One-Click Hackathon Personas")
    selected_persona_name = st.selectbox(
        "Load Pre-Configured Citizen Profile:",
        ["Custom Input"] + list(DEMO_PERSONAS.keys()),
    )

    if selected_persona_name != "Custom Input":
        st.session_state.profile = DEMO_PERSONAS[selected_persona_name]()
        memory.save_profile("active_session", st.session_state.profile)
        st.success(f"Loaded & Saved: {selected_persona_name}")

    st.markdown("---")
    st.subheader("🌐 Language & Voice Preference")
    lang = st.radio("Response Language:", ["English", "हिंदी (Hindi)"])
    lang_code = "hi" if "हिंदी" in lang else "en"

    st.markdown("---")
    st.subheader("📄 Document Upload (Aadhaar / Ration Card)")
    uploaded_file = st.file_uploader(
        "Upload document photo (JPG/PNG)", type=["png", "jpg", "jpeg"]
    )
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = Path(tmp.name)

        ocr = DocumentOCR()
        extracted_text = ocr.extract_text(tmp_path)
        doc_facts = ocr.parse_profile_from_document(extracted_text, filename=uploaded_file.name)
        for k, v in doc_facts.items():
            st.session_state.profile.set_fact(k, v, confidence=0.95, source=Source.DOCUMENT)
        memory.save_profile("active_session", st.session_state.profile)
        st.success(f"Extracted from document: {', '.join(doc_facts.keys()) or 'Document verified'}")

    st.markdown("---")
    st.subheader("📋 Current Citizen Facts")
    known = st.session_state.profile.known_fields()
    if known:
        for k, v in known.items():
            st.write(f"• **{k}**: `{v}`")
    else:
        st.info("No profile facts recorded yet.")

    if st.button("🔄 Reset Profile & Session", use_container_width=True):
        st.session_state.profile = CitizenProfile()
        memory.save_profile("active_session", st.session_state.profile)
        if "last_state" in st.session_state:
            del st.session_state["last_state"]
        st.rerun()

# Main input section
user_text = st.text_area(
    "Describe your situation / Aapki samasya ya sthiti batayein:",
    placeholder="e.g. Mai UP ke gaon me kheti karta hu, 2 acre jameen hai, aay 1.5 lakh hai aur BPL card hai. Konsi scheme milegi?",
    height=80,
)

if user_text:
    intake = NaturalLanguageIntake()
    st.session_state.profile = intake.parse_user_input(user_text, existing_profile=st.session_state.profile)
    memory.save_profile("active_session", st.session_state.profile)

col1, col2 = st.columns([1, 4])
with col1:
    run_btn = st.button("🚀 Match My Schemes", type="primary", use_container_width=True)

if run_btn or "last_state" in st.session_state:
    if run_btn:
        with st.spinner("Agentic pipeline executing (Planner -> Matcher -> Verifier -> Critic)..."):
            graph = build_graph()
            initial_state = AgentState(
                profile=st.session_state.profile,
                user_query=user_text or "all eligible schemes",
                language=lang_code
            )
            final_state = graph.invoke(initial_state)
            st.session_state.last_state = final_state
            # Persist match results in SQLite
            memory.save_matches("active_session", final_state.get("match_results", []))
    else:
        final_state = st.session_state.last_state

    # 1. Live Agent Trace Panel (Crucial for Hackathon evaluation)
    with st.expander("🔍 Live Agent Trace Panel (Internal Multi-Agent Audit Log)", expanded=True):
        st.markdown("**Chronological Sub-Agent Reasoning & Execution Steps:**")
        trace_steps = final_state.get("trace_steps", [])
        for i, t in enumerate(trace_steps, 1):
            agent_emoji = {
                "Planner": "🧠",
                "Matcher": "⚖️",
                "Gap-Asker": "❓",
                "Verifier": "✅",
                "Critic": "🛡️",
                "Orchestrator": "🎯",
            }.get(t.agent_name, "🤖")

            st.markdown(f"**Step {i}: {agent_emoji} {t.agent_name}** — *{t.action}*")
            if t.details:
                st.json(t.details)

    # 2. Results Layout
    match_results = final_state.get("match_results", [])
    eligible = [m for m in match_results if m.status == EligibilityStatus.ELIGIBLE]
    almost = [m for m in match_results if m.status == EligibilityStatus.ALMOST]

    # Voice Briefing Player
    st.subheader("🔊 Multimodal Audio Briefing")
    if eligible:
        top_scheme = eligible[0].scheme_name
        briefing_text = (
            f"बधाई हो! आप {top_scheme} समेत कुल {len(eligible)} योजनाओं के लिए पात्र हैं।"
            if lang_code == "hi"
            else f"Congratulations! You qualify for {len(eligible)} government schemes including {top_scheme}."
        )
    else:
        briefing_text = (
            "वर्तमान में कोई पूर्ण पात्र योजना नहीं मिली है, कृपया अतिरिक्त जानकारी दें।"
            if lang_code == "hi"
            else "No fully eligible schemes matched yet. Please provide additional information."
        )

    audio_path = text_to_speech(briefing_text, language=lang_code)
    if audio_path.exists():
        st.audio(str(audio_path), format="audio/mp3")

    # Interactive Gap-Asking Follow-up
    pending_qs = final_state.get("pending_questions", [])
    if almost and pending_qs:
        st.markdown("---")
        top_q = pending_qs[-1]
        st.warning(f"❓ **Agent Follow-Up Question**: {top_q}")
        with st.form("gap_answer_form"):
            user_ans = st.text_input("Type your answer here / Apna jawab yahan likhein:")
            submitted = st.form_submit_button("Submit Answer & Re-Match Schemes")
            if submitted and user_ans:
                intake = NaturalLanguageIntake()
                st.session_state.profile = intake.parse_user_input(user_ans, existing_profile=st.session_state.profile)
                memory.save_profile("active_session", st.session_state.profile)
                if "last_state" in st.session_state:
                    del st.session_state["last_state"]
                st.rerun()

    # Eligible Schemes Display
    st.subheader(f"✅ Verified Eligible Schemes ({len(eligible)})")
    if not eligible:
        st.warning("No fully eligible schemes matched. Check the 'Almost Eligible' section below.")

    for m in eligible:
        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"### {m.scheme_name}")
                st.markdown(f"**💰 Benefit**: {m.benefit_summary}")
                st.markdown(f"**🏛️ Deciding Rule / Reason**: {', '.join(m.satisfied_reasons)}")
                st.markdown(f"**🔗 Verified Official Portal**: [{m.official_url}]({m.official_url})")

                if m.documents_required:
                    st.markdown("**📄 Mandatory Documents Checklist:**")
                    for doc in m.documents_required:
                        st.checkbox(doc, value=True, key=f"{m.scheme_id}_{doc}")

            with cols[1]:
                st.markdown("**⚡ One-Click Actions**")
                # PDF Generation
                pdf_path = generate_application_pdf(st.session_state.profile, m)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Pre-filled PDF",
                        data=f.read(),
                        file_name=f"Application_{m.scheme_id}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{m.scheme_id}",
                        use_container_width=True
                    )

                # Calendar Reminder (.ics)
                ics_path = create_scheme_reminder_ics(m)
                with open(ics_path, "rb") as f:
                    st.download_button(
                        label="📅 Add .ics Reminder",
                        data=f.read(),
                        file_name=f"Reminder_{m.scheme_id}.ics",
                        mime="text/calendar",
                        key=f"ics_{m.scheme_id}",
                        use_container_width=True
                    )

    # Physical Office Guidance
    guidance = get_csc_office_guidance(st.session_state.profile)
    with st.expander("🏢 Nearest Common Service Center (CSC) & Submission Office"):
        st.info(guidance["instructions"])
        st.markdown(f"[Find your nearest CSC center online]({guidance['csc_locator_url']})")

    # Almost Eligible Schemes
    if almost:
        st.subheader(f"⚠️ Almost Eligible ({len(almost)}) — Missing Key Info")
        for m in almost[:4]:
            with st.container(border=True):
                st.markdown(f"#### {m.scheme_name}")
                st.write(f"**Missing Information Needed**: `{', '.join(m.missing_fields)}`")
                st.markdown(f"**Official Link**: [{m.official_url}]({m.official_url})")
