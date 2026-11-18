"""Streamlit UI for YojanaAgent featuring Live Agent Trace Panel and Action Downloads."""

import streamlit as st
from brain.graph import build_graph
from experience.actions.calendar_reminders import create_scheme_reminder_ics
from experience.actions.office_guidance import get_csc_office_guidance
from experience.actions.pdf_filler import generate_application_pdf
from experience.intake.hinglish import NaturalLanguageIntake
from experience.intake.voice import text_to_speech
from experience.personas.demo_profiles import DEMO_PERSONAS
from shared.schemas import AgentState, CitizenProfile, EligibilityStatus

st.set_page_config(
    page_title="YojanaAgent - Autonomous Scheme Matcher",
    page_icon="🇮🇳",
    layout="wide",
)

# Header
st.title("🇮🇳 YojanaAgent: Autonomous Government Scheme-Matching Assistant")
st.caption("Tell us your situation in Hindi, Hinglish, or English. We find, verify, and fill your schemes autonomously.")

# Sidebar: One-Click Demo Personas & Inputs
with st.sidebar:
    st.header("⚡ One-Click Hackathon Personas")
    selected_persona_name = st.selectbox(
        "Load Pre-Configured Citizen Profile:",
        ["Custom Input"] + list(DEMO_PERSONAS.keys()),
    )

    if selected_persona_name != "Custom Input":
        profile: CitizenProfile = DEMO_PERSONAS[selected_persona_name]()
        st.success(f"Loaded: {selected_persona_name}")
    else:
        profile = CitizenProfile()

    st.markdown("---")
    st.subheader("🌐 Language & Voice Preference")
    lang = st.radio("Response Language:", ["English", "हिंदी (Hindi)"])
    lang_code = "hi" if "हिंदी" in lang else "en"

    st.markdown("---")
    st.subheader("📋 Current Citizen Facts")
    known = profile.known_fields()
    if known:
        for k, v in known.items():
            st.write(f"• **{k}**: `{v}`")
    else:
        st.info("No profile facts recorded yet.")

# Main input section
user_text = st.text_area(
    "Describe your situation / Aapki samasya ya sthiti batayein:",
    placeholder="e.g. Mai UP ke gaon me kheti karta hu, 2 acre jameen hai aur BPL card hai. Konsi scheme milegi?",
    height=80,
)

if user_text:
    intake = NaturalLanguageIntake()
    profile = intake.parse_user_input(user_text, existing_profile=profile)

col1, col2 = st.columns([1, 4])
with col1:
    run_btn = st.button("🚀 Match My Schemes", type="primary", use_container_width=True)

if run_btn:
    with st.spinner("Agentic pipeline executing (Planner -> Matcher -> Verifier -> Critic)..."):
        graph = build_graph()
        initial_state = AgentState(
            profile=profile,
            user_query=user_text or "all eligible schemes",
            language=lang_code
        )
        final_state = graph.invoke(initial_state)

    # 1. Live Agent Trace Panel (Crucial for Hackathon evaluation)
    with st.expander("🔍 Live Agent Trace Panel (Internal Reasoning & Audit)", expanded=True):
        st.markdown("**Chronological Sub-Agent Actions:**")
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
                pdf_path = generate_application_pdf(profile, m)
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
    guidance = get_csc_office_guidance(profile)
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
