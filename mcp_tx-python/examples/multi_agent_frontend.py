"""
Streamlit Frontend for the Multi-Agent Research Assistant
"""

import time
import uuid

import streamlit as st

# This imports the backend functions. In a real distributed setup,
# this would be an API client.
from multi_agent_backend import get_research_status, provide_approval, start_research

# --- Page Configuration ---
st.set_page_config(
    page_title="Autonomous Research Agent",
    page_icon="🤖",
    layout="wide",
)

# --- State Management ---
if "research_id" not in st.session_state:
    st.session_state.research_id = None
if "last_status" not in st.session_state:
    st.session_state.last_status = {}

# --- UI Components ---


def render_header():
    st.title("🤖 Autonomous Multi-Agent Research Assistant")
    st.markdown("Powered by **MCP-Tx** for long-running, reliable AI agent orchestration.")


def render_input_form():
    st.header("1. Start a New Research Task")
    with st.form("research_form"):
        companies_input = st.text_input(
            "Companies to Research",
            "Apple, Google, Microsoft",
            help="Enter a comma-separated list of companies.",
        )
        submitted = st.form_submit_button("🚀 Launch Agents", type="primary")

        if submitted:
            companies = [c.strip() for c in companies_input.split(",") if c.strip()]
            if companies:
                research_id = f"research-{uuid.uuid4()}"
                st.session_state.research_id = research_id
                start_research(research_id, companies)
                st.rerun()
            else:
                st.error("Please enter at least one company name.")


def render_progress_view(status: dict):
    st.header("2. Research Progress")

    status_text = status.get("status", "unknown").replace("_", " ").title()
    st.info(f"**Status:** {status_text}")

    if status.get("error"):
        st.error(f"**Error:** {status.get('error')}")

    if "agent_results" in status:
        with st.expander("Agent Results", expanded=False):
            st.json(status["agent_results"])


def render_approval_view(status: dict):
    st.header("3. Human-in-the-Loop: Final Approval")
    st.warning("The AI agents have completed their tasks. Please review and approve the final report.")

    draft_report = status.get("draft_report", "No draft available.")

    with st.form("approval_form"):
        edited_report = st.text_area("Final Report", value=draft_report, height=400)

        col1, col2 = st.columns(2)
        with col1:
            approved = st.form_submit_button("✅ Approve and Publish", type="primary")
        with col2:
            rejected = st.form_submit_button("❌ Reject")

        if approved:
            provide_approval(st.session_state.research_id, edited_report, approved=True)
            st.rerun()
        if rejected:
            provide_approval(st.session_state.research_id, edited_report, approved=False)
            st.rerun()


def render_completion_view(status: dict):
    st.header("4. Research Complete")
    st.success("The research task has been successfully completed.")

    final_report = status.get("final_report", "No final report available.")

    with st.container(border=True):
        st.markdown(final_report)

    if st.button("🔄 Start Another Research Task"):
        st.session_state.research_id = None
        st.rerun()


# --- Main App Logic ---


def main():
    render_header()

    research_id = st.session_state.research_id

    if not research_id:
        render_input_form()
    else:
        status = get_research_status(research_id)
        st.session_state.last_status = status

        if status["status"] in ["starting", "in_progress", "publishing"]:
            render_progress_view(status)
            time.sleep(2)
            st.rerun()
        elif status["status"] == "waiting_for_approval":
            render_progress_view(status)
            render_approval_view(status)
        elif status["status"] == "completed":
            render_completion_view(status)
        elif status["status"] == "failed":
            render_progress_view(status)
            if st.button("🔄 Start New Research"):
                st.session_state.research_id = None
                st.rerun()
        else:
            st.info("Waiting for the research task to be initialized...")
            time.sleep(1)
            st.rerun()


if __name__ == "__main__":
    main()
