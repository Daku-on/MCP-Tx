"""
Streamlit Frontend for the Multi-Agent Research Assistant
"""

import time
import uuid

import streamlit as st

# This imports the backend functions. In a real distributed setup,
# this would be an API client.
from multi_agent_backend import get_research_status, provide_approval, start_research

# --- Language Translations ---
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "page_title": "Autonomous Research Agent",
        "title": "🤖 Autonomous Multi-Agent Research Assistant",
        "subtitle": "Powered by **MCP-Tx** for long-running, reliable AI agent orchestration.",
        "header_start": "1. Start a New Research Task",
        "companies_label": "Companies to Research",
        "companies_placeholder": "Apple, Google, Microsoft",
        "companies_help": "Enter a comma-separated list of companies.",
        "launch_button": "🚀 Launch Agents",
        "error_no_companies": "Please enter at least one company name.",
        "header_progress": "2. Research Progress",
        "status_label": "**Status:**",
        "error_label": "**Error:**",
        "agent_results": "Agent Results",
        "header_approval": "3. Human-in-the-Loop: Final Approval",
        "approval_warning": "The AI agents have completed their tasks. Please review and approve the final report.",
        "final_report_label": "Final Report",
        "approve_button": "✅ Approve and Publish",
        "reject_button": "❌ Reject",
        "header_complete": "4. Research Complete",
        "complete_message": "The research task has been successfully completed.",
        "no_report": "No final report available.",
        "start_another": "🔄 Start Another Research Task",
        "start_new": "🔄 Start New Research",
        "waiting_init": "Waiting for the research task to be initialized...",
        "no_draft": "No draft available.",
        "status_starting": "Starting",
        "status_in_progress": "In Progress",
        "status_waiting_for_approval": "Waiting for Approval",
        "status_publishing": "Publishing",
        "status_completed": "Completed",
        "status_failed": "Failed",
        "status_cancelled": "Cancelled",
        "status_unknown": "Unknown",
    },
    "ja": {
        "page_title": "自律型リサーチエージェント",
        "title": "🤖 自律型マルチエージェント・リサーチアシスタント",
        "subtitle": "**MCP-Tx**による長時間実行・高信頼性AIエージェント制御",
        "header_start": "1. 新しいリサーチタスクを開始",
        "companies_label": "調査対象企業",
        "companies_placeholder": "Apple, Google, Microsoft",
        "companies_help": "カンマ区切りで企業名を入力してください。",
        "launch_button": "🚀 エージェントを起動",
        "error_no_companies": "少なくとも1社の企業名を入力してください。",
        "header_progress": "2. リサーチ進行状況",
        "status_label": "**ステータス:**",
        "error_label": "**エラー:**",
        "agent_results": "エージェント結果",
        "header_approval": "3. ヒューマン・イン・ザ・ループ: 最終承認",
        "approval_warning": "AIエージェントがタスクを完了しました。最終レポートを確認して承認してください。",
        "final_report_label": "最終レポート",
        "approve_button": "✅ 承認して公開",
        "reject_button": "❌ 却下",
        "header_complete": "4. リサーチ完了",
        "complete_message": "リサーチタスクが正常に完了しました。",
        "no_report": "最終レポートがありません。",
        "start_another": "🔄 別のリサーチタスクを開始",
        "start_new": "🔄 新しいリサーチを開始",
        "waiting_init": "リサーチタスクの初期化を待っています...",
        "no_draft": "ドラフトがありません。",
        "status_starting": "開始中",
        "status_in_progress": "進行中",
        "status_waiting_for_approval": "承認待ち",
        "status_publishing": "公開中",
        "status_completed": "完了",
        "status_failed": "失敗",
        "status_cancelled": "キャンセル",
        "status_unknown": "不明",
    },
}

# --- Page Configuration ---
st.set_page_config(
    page_title="Autonomous Research Agent / 自律型リサーチエージェント",
    page_icon="🤖",
    layout="wide",
)

# --- State Management ---
if "research_id" not in st.session_state:
    st.session_state.research_id = None
if "last_status" not in st.session_state:
    st.session_state.last_status = {}
if "language" not in st.session_state:
    st.session_state.language = "en"

# --- Helper Functions ---


def t(key: str) -> str:
    """Get translation for the current language."""
    return TRANSLATIONS[st.session_state.language].get(key, key)


def get_status_text(status: str) -> str:
    """Get localized status text."""
    status_key = f"status_{status.replace('_', '')}"
    return t(status_key)


# --- UI Components ---


def render_language_toggle():
    """Render language toggle in sidebar."""
    with st.sidebar:
        st.markdown("### Language / 言語")

        # Language selection
        language_options = {"en": "🇺🇸 English", "ja": "🇯🇵 日本語"}

        selected_lang = st.selectbox(
            "Select Language / 言語選択",
            options=list(language_options.keys()),
            format_func=lambda x: language_options[x],
            index=0 if st.session_state.language == "en" else 1,
            key="language_selector",
        )

        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()


def render_header():
    render_language_toggle()
    st.title(t("title"))
    st.markdown(t("subtitle"))


def render_input_form():
    st.header(t("header_start"))
    with st.form("research_form"):
        companies_input = st.text_input(
            t("companies_label"),
            t("companies_placeholder"),
            help=t("companies_help"),
        )
        submitted = st.form_submit_button(t("launch_button"), type="primary")

        if submitted:
            companies = [c.strip() for c in companies_input.split(",") if c.strip()]
            if companies:
                research_id = f"research-{uuid.uuid4()}"
                st.session_state.research_id = research_id
                # Store language preference in session state for backend
                start_research(research_id, companies)
                st.rerun()
            else:
                st.error(t("error_no_companies"))


def render_progress_view(status: dict):
    st.header(t("header_progress"))

    status_text = get_status_text(status.get("status", "unknown"))
    st.info(f"{t('status_label')} {status_text}")

    if status.get("error"):
        st.error(f"{t('error_label')} {status.get('error')}")

    if "agent_results" in status:
        with st.expander(t("agent_results"), expanded=False):
            st.json(status["agent_results"])


def render_approval_view(status: dict):
    st.header(t("header_approval"))
    st.warning(t("approval_warning"))

    draft_report = status.get("draft_report", t("no_draft"))

    with st.form("approval_form"):
        edited_report = st.text_area(t("final_report_label"), value=draft_report, height=400)

        col1, col2 = st.columns(2)
        with col1:
            approved = st.form_submit_button(t("approve_button"), type="primary")
        with col2:
            rejected = st.form_submit_button(t("reject_button"))

        if approved:
            provide_approval(st.session_state.research_id, edited_report, approved=True)
            st.rerun()
        if rejected:
            provide_approval(st.session_state.research_id, edited_report, approved=False)
            st.rerun()


def render_completion_view(status: dict):
    st.header(t("header_complete"))
    st.success(t("complete_message"))

    final_report = status.get("final_report", t("no_report"))

    with st.container(border=True):
        st.markdown(final_report)

    if st.button(t("start_another")):
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
            if st.button(t("start_new")):
                st.session_state.research_id = None
                st.rerun()
        else:
            st.info(t("waiting_init"))
            time.sleep(1)
            st.rerun()


if __name__ == "__main__":
    main()
