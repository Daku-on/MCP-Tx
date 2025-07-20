#!/usr/bin/env python3
"""
Smart Research Assistant - Consolidated Streamlit Frontend

A complete web interface for the Smart Research Assistant with all
components, state management, and utilities in a single file.

Usage:
    streamlit run research_frontend.py
"""

import re
import time
from datetime import datetime
from typing import Any

import streamlit as st
from research_backend import research_assistant

# =============================================================================
# STATE MANAGEMENT
# =============================================================================


class SessionStateManager:
    """Manages Streamlit session state with type safety and validation."""

    # Session state keys
    RESEARCH_HISTORY = "research_history"
    CURRENT_RESEARCH_ID = "current_research_id"
    AUTO_REFRESH = "auto_refresh"
    VIEW_RESULT = "view_result"

    @classmethod
    def initialize(cls):
        """Initialize all session state variables with default values."""
        defaults = {
            cls.RESEARCH_HISTORY: [],
            cls.CURRENT_RESEARCH_ID: None,
            cls.AUTO_REFRESH: True,
        }

        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @classmethod
    def get_research_history(cls) -> list[dict[str, Any]]:
        """Get research history from session state."""
        return st.session_state.get(cls.RESEARCH_HISTORY, [])

    @classmethod
    def add_to_history(cls, research_data: dict[str, Any]):
        """Add research data to history."""
        history = cls.get_research_history()

        # Avoid duplicates by checking research_id
        research_id = research_data.get("research_id", "unknown")
        if not any(item.get("research_id") == research_id for item in history):
            history.append(research_data)
            st.session_state[cls.RESEARCH_HISTORY] = history

    @classmethod
    def get_current_research_id(cls) -> str | None:
        """Get current research ID."""
        return st.session_state.get(cls.CURRENT_RESEARCH_ID)

    @classmethod
    def set_current_research_id(cls, research_id: str | None):
        """Set current research ID."""
        st.session_state[cls.CURRENT_RESEARCH_ID] = research_id

    @classmethod
    def clear_current_research(cls):
        """Clear current research session."""
        st.session_state[cls.CURRENT_RESEARCH_ID] = None
        if cls.VIEW_RESULT in st.session_state:
            del st.session_state[cls.VIEW_RESULT]

    @classmethod
    def get_auto_refresh(cls) -> bool:
        """Get auto-refresh setting."""
        return st.session_state.get(cls.AUTO_REFRESH, True)

    @classmethod
    def set_auto_refresh(cls, enabled: bool):
        """Set auto-refresh setting."""
        st.session_state[cls.AUTO_REFRESH] = enabled

    @classmethod
    def set_view_result(cls, result: dict[str, Any]):
        """Set result to view from history."""
        st.session_state[cls.VIEW_RESULT] = result

    @classmethod
    def get_view_result(cls) -> dict[str, Any] | None:
        """Get result being viewed from history."""
        return st.session_state.get(cls.VIEW_RESULT)

    @classmethod
    def clear_view_result(cls):
        """Clear the view result."""
        if cls.VIEW_RESULT in st.session_state:
            del st.session_state[cls.VIEW_RESULT]

    @classmethod
    def get_history_item_by_index(cls, index: int) -> dict[str, Any] | None:
        """Get history item by index (from most recent)."""
        history = cls.get_research_history()
        if 0 <= index < len(history):
            return list(reversed(history))[index]
        return None

    @classmethod
    def get_session_stats(cls) -> dict[str, Any]:
        """Get session statistics."""
        history = cls.get_research_history()
        current_id = cls.get_current_research_id()

        return {
            "total_research_sessions": len(history),
            "current_research_active": current_id is not None,
            "auto_refresh_enabled": cls.get_auto_refresh(),
            "last_research_time": history[-1]["timestamp"] if history else None,
        }


class ApplicationState:
    """Manages application-wide state and navigation."""

    def __init__(self):
        self.session_manager = SessionStateManager()
        self._initialize_app_state()

    def _initialize_app_state(self):
        """Initialize application state."""
        self.session_manager.initialize()

    def start_new_research(self, research_id: str) -> None:
        """Start a new research session."""
        self.session_manager.clear_view_result()
        self.session_manager.set_current_research_id(research_id)

    def complete_research(self, result: dict[str, Any], mcp_tx_stats: dict[str, Any]) -> None:
        """Complete current research session."""
        history_entry = {
            "timestamp": datetime.now(),
            "query": self._extract_query_from_result(result),
            "research_id": result.get("research_id", "unknown"),
            "result": result,
            "mcp_tx_stats": mcp_tx_stats,
        }

        self.session_manager.add_to_history(history_entry)

    def view_historical_result(self, history_index: int) -> bool:
        """View a result from history."""
        history_item = self.session_manager.get_history_item_by_index(history_index)
        if history_item:
            self.session_manager.clear_current_research()
            self.session_manager.set_view_result(history_item["result"])
            return True
        return False

    def clear_current_session(self):
        """Clear current research session."""
        self.session_manager.clear_current_research()

    def refresh_page(self):
        """Trigger page refresh."""
        st.rerun()

    def _extract_query_from_result(self, result: dict[str, Any]) -> str:
        """Extract query from result with fallback logic."""
        if isinstance(result, dict):
            if "report" in result and isinstance(result["report"], dict):
                if "query" in result["report"]:
                    return result["report"]["query"]
                elif "metadata" in result["report"] and "query" in result["report"]["metadata"]:
                    return result["report"]["metadata"]["query"]
            elif "query" in result:
                return result["query"]

        return "Unknown Query"

    def get_current_state(self) -> dict[str, Any]:
        """Get current application state summary."""
        return {
            "current_research_id": self.session_manager.get_current_research_id(),
            "viewing_history": self.session_manager.get_view_result() is not None,
            "session_stats": self.session_manager.get_session_stats(),
            "auto_refresh": self.session_manager.get_auto_refresh(),
        }


class NavigationController:
    """Controls application navigation and page flow."""

    def __init__(self, app_state: ApplicationState):
        self.app_state = app_state

    def handle_form_submission(self, research_id: str) -> str:
        """Handle research form submission."""
        self.app_state.start_new_research(research_id)
        self.app_state.refresh_page()
        return "research_started"

    def handle_research_completion(self, result: dict[str, Any], mcp_tx_stats: dict[str, Any]) -> str:
        """Handle research completion."""
        self.app_state.complete_research(result, mcp_tx_stats)
        return "research_completed"

    def handle_new_research_request(self) -> str:
        """Handle new research request."""
        self.app_state.clear_current_session()
        self.app_state.refresh_page()
        return "new_research_started"

    def handle_history_view(self, history_index: int) -> str:
        """Handle viewing historical result."""
        if self.app_state.view_historical_result(history_index):
            self.app_state.refresh_page()
            return "history_viewed"
        return "history_view_failed"

    def handle_clear_current(self) -> str:
        """Handle clearing current research."""
        self.app_state.clear_current_session()
        self.app_state.refresh_page()
        return "current_cleared"

    def handle_refresh(self) -> str:
        """Handle manual refresh."""
        self.app_state.refresh_page()
        return "page_refreshed"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def safe_get(data: dict[str, Any], key: str, default: Any = "N/A") -> Any:
    """Safely get value from dictionary with fallback."""
    return data.get(key, default) if isinstance(data, dict) else default


def extract_query_from_result(result: dict[str, Any]) -> str:
    """Extract query from result with fallback logic."""
    if isinstance(result, dict):
        if "report" in result and isinstance(result["report"], dict):
            if "query" in result["report"]:
                return result["report"]["query"]
            elif "metadata" in result["report"] and "query" in result["report"]["metadata"]:
                return result["report"]["metadata"]["query"]
        elif "query" in result:
            return result["query"]
    return "Unknown Query"


def extract_report_content(result: dict[str, Any]) -> str | None:
    """Extract report content from result with safe access."""
    if isinstance(result, dict) and "report" in result:
        report = result["report"]
        if isinstance(report, dict):
            return report.get("report") or report.get("content")
        elif isinstance(report, str):
            return report
    return None


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================


class ValidationUtils:
    """Utility class for input validation and error checking."""

    @staticmethod
    def validate_research_query(query: str) -> tuple[bool, str]:
        """Validate research query input."""
        if not query or not query.strip():
            return False, "Research query cannot be empty"

        if len(query.strip()) < 3:
            return False, "Research query must be at least 3 characters"

        if len(query.strip()) > 500:
            return False, "Research query must be less than 500 characters"

        return True, ""

    @staticmethod
    def validate_research_id(research_id: str) -> tuple[bool, str]:
        """Validate custom research ID."""
        if not research_id:
            return True, ""  # Empty is allowed (will use auto-generated)

        if len(research_id) > 100:
            return False, "Research ID must be less than 100 characters"

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9_-]+$", research_id):
            return False, "Research ID can only contain letters, numbers, hyphens, and underscores"

        return True, ""


# =============================================================================
# UI COMPONENTS
# =============================================================================


def render_header():
    """Display application header and branding."""
    st.set_page_config(
        page_title="Smart Research Assistant", page_icon="🔬", layout="wide", initial_sidebar_state="expanded"
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("🔬 Smart Research Assistant")
        st.markdown("*Powered by MCP-Tx for Reliable AI Research*")

        st.markdown(
            """
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                    padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">
            <p style="color: white; margin: 0; text-align: center;">
                <strong>🛡️ MCP-Tx Reliability Features:</strong>
                Automatic Retry • Idempotency • ACK/NACK Tracking • Error Recovery
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_research_form() -> str | None:
    """Render the research input form."""
    st.header("🔍 Start New Research")

    with st.form("research_form"):
        col1, col2 = st.columns([3, 1])

        with col1:
            query = st.text_input(
                "Research Query",
                placeholder="Enter your research question (e.g., 'AI impact on software development 2024')",
                help="Describe what you want to research. The assistant will search, analyze, and fact-check.",
            )

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("🚀 Start Research", type="primary", use_container_width=True)

        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            col1, col2 = st.columns(2)
            with col1:
                custom_id = st.text_input("Custom Research ID (Optional)", placeholder="research_custom_001")
            with col2:
                st.markdown("**Research will include:**")
                st.markdown("- 🔍 Web search (6 sources)")
                st.markdown("- 📊 Content analysis (3 sources)")
                st.markdown("- ✅ Fact checking (2 claims)")
                st.markdown("- 📄 Report generation")
                st.markdown("- 💾 Persistent storage")

        # FastMCP-Tx Configuration Details
        with st.expander("🛡️ FastMCP-Tx Decorator Configuration"):
            st.markdown("""
            **How @app.tool() Decorators Transform Functions:**

            FastMCP-Tx automatically wraps each research function with reliability features:
            """)

            st.code(
                """
@app.tool(
    retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=2000, backoff_multiplier=2.0),
    timeout_ms=15000,
    idempotency_key_generator=lambda args: f"search-{hash(args['query'])}",
)
async def web_search(query: str, num_results: int = 5):
    # Your regular function code here
    # FastMCP-Tx adds: retry, timeout, idempotency, ACK tracking
    return search_results
            """,
                language="python",
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("""
                **Reliability Features Added:**
                - 🔄 **Automatic Retry** with exponential backoff
                - ⏱️ **Timeout Protection** prevents infinite waiting
                - 🔒 **Idempotency Keys** prevent duplicate execution
                - ✅ **ACK/NACK Tracking** confirms completion
                - 📊 **Real-time Metrics** for monitoring
                """)

            with col2:
                st.markdown("""
                **Per-Tool Configuration:**
                - **🔍 Web Search**: 3 attempts, 15s timeout
                - **📊 Content Analysis**: 5 attempts, idempotent by content
                - **✅ Fact Checking**: 3 attempts, 20s timeout
                - **📄 Report Generation**: 2 attempts, 30s timeout
                - **💾 Save Results**: 2 attempts, idempotent by ID
                """)

        if submit_button and query:
            if research_assistant.is_research_active():
                st.error("⚠️ Research already in progress. Please wait for completion.")
                return None
            else:
                research_id = research_assistant.start_research(query, custom_id if custom_id else None)
                st.success(f"✅ Research started! ID: {research_id}")
                return research_id
        elif submit_button:
            st.error("Please enter a research query.")

    return None


def render_progress(current_research_id: str) -> bool:
    """Render progress tracking component."""
    if not current_research_id:
        return False

    progress_data = research_assistant.get_progress()

    if progress_data["current_status"] == "ready":
        return False

    st.header("📊 Research Progress")

    # Progress overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Status",
            progress_data["current_status"].title(),
            delta=progress_data["current_step"].replace("_", " ").title() if progress_data["current_step"] else None,
        )

    with col2:
        st.metric(
            "Progress",
            f"{progress_data['progress_percentage']}%",
            delta=f"{progress_data['steps_completed']}/{progress_data['total_steps']} steps",
        )

    with col3:
        if progress_data.get("mcp_tx_stats"):
            st.metric(
                "MCP-Tx Reliability",
                progress_data["mcp_tx_stats"].get("reliability_rate", "N/A"),
                delta=f"{progress_data['mcp_tx_stats'].get('successful_operations', 0)} successful steps",
            )
        else:
            st.metric("MCP-Tx Reliability", "Calculating...", delta="In progress")

    with col4:
        st.metric(
            "Last Update",
            progress_data["last_update"].strftime("%H:%M:%S") if progress_data.get("last_update") else "N/A",
        )

    # Progress bar
    progress_value = min(max(progress_data["progress_percentage"] / 100, 0.0), 1.0)
    st.progress(progress_value)

    # Current step indicator
    step_names = {
        "initialization": "🔧 Initialization",
        "web_search": "🔍 Web Search",
        "content_analysis": "📊 Content Analysis",
        "fact_checking": "✅ Fact Checking",
        "report_generation": "📄 Report Generation",
        "save_results": "💾 Save Results",
    }

    current_step = progress_data.get("current_step")
    if current_step in step_names:
        st.info(f"**Current Step:** {step_names[current_step]}")

    # Real-time messages
    if progress_data.get("messages"):
        with st.expander("📝 Detailed Progress Log", expanded=True):
            for message in progress_data["messages"][-10:]:  # Show last 10 messages
                st.text(f"[{message['timestamp']}] {message['step']}: {message['message']}")

    # Error display
    if progress_data.get("error"):
        st.error(f"❌ Error: {progress_data['error']}")

    # Auto-refresh logic
    auto_refresh = st.session_state.get("auto_refresh", True)
    is_running = progress_data["current_status"] in ["running", "in_progress"]

    if auto_refresh and is_running:
        time.sleep(2)
        return True
    return False


def render_results() -> str | None:
    """Render research results."""
    progress_data = research_assistant.get_progress()

    if progress_data["current_status"] != "completed" or not progress_data.get("result"):
        return None

    result = progress_data["result"]
    mcp_tx_stats = progress_data["mcp_tx_stats"]

    st.header("📋 Research Results")

    # Results overview
    metadata = result.get("metadata", {})
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Sources Found", safe_get(metadata, "sources_found"))
    with col2:
        st.metric("Analyses Completed", safe_get(metadata, "analyses_completed"))
    with col3:
        st.metric("Fact Checks", safe_get(metadata, "fact_checks_performed"))

    # Research Report
    st.subheader("📄 Research Report")

    report_content = extract_report_content(result)
    if report_content:
        tab1, tab2 = st.tabs(["📖 Formatted Report", "🔧 Raw Content"])

        with tab1:
            st.markdown(report_content)

        with tab2:
            st.json(result.get("report", {}))
    else:
        st.warning("⚠️ Report content not available in expected format")
        with st.expander("🔍 Debug: View Raw Result"):
            st.json(result)

    # MCP-Tx Reliability Metrics
    st.subheader("🛡️ MCP-Tx Reliability Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Attempts",
            mcp_tx_stats.get("total_mcp_tx_attempts", 0),
            help="Total number of MCP-Tx request attempts across all steps",
        )

    with col2:
        st.metric(
            "Success Rate",
            mcp_tx_stats.get("reliability_rate", "0%"),
            help="Percentage of successful MCP-Tx operations",
        )

    with col3:
        st.metric(
            "Successful Steps",
            mcp_tx_stats.get("successful_operations", 0),
            help="Number of research steps completed successfully",
        )

    # MCP-Tx Step Details
    if mcp_tx_stats.get("steps_details"):
        with st.expander("🔍 MCP-Tx Step Details", expanded=False):
            for step in mcp_tx_stats["steps_details"]:
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.text(f"Step: {step['step']}")
                with col2:
                    st.text(f"Attempts: {step['attempts']}")
                with col3:
                    status = "✅ ACK" if step["ack"] else "❌ NACK"
                    st.text(f"Status: {status}")
                with col4:
                    duplicate = "🔄 Duplicate" if step.get("duplicate", False) else "🆕 New"
                    st.text(f"Type: {duplicate}")

                st.divider()

    # Idempotency Guarantees Showcase
    with st.expander("🔒 Idempotency Guarantees", expanded=False):
        st.markdown("**FastMCP-Tx prevents duplicate operations using idempotency keys:**")

        if result and result.get("research_id"):
            research_id = result["research_id"]
            st.markdown("**This research session used these idempotency keys:**")

            st.code(
                f"""
# Each operation gets a unique, deterministic key:
web_search     → "search-{research_id}"
content_analysis → "analyze-{research_id}-0", "analyze-{research_id}-1", "analyze-{research_id}-2"
fact_checking  → "factcheck-{research_id}-0", "factcheck-{research_id}-1"
report_generation → "report-{research_id}"
save_results   → "save-{research_id}"
            """,
                language="text",
            )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **🛡️ Protection Against:**
            - Duplicate API calls if network fails
            - Double-billing for expensive operations
            - Inconsistent data from repeated writes
            - Race conditions in concurrent operations
            - Accidental button double-clicks
            """)

        with col2:
            st.markdown("""
            **✅ Guarantees Provided:**
            - Same request = Same result (always)
            - No duplicate execution (safe retries)
            - Consistent state across failures
            - Cost protection for paid APIs
            - Data integrity preservation
            """)

        st.info("""
        💡 **How it works**: FastMCP-Tx generates deterministic keys from request parameters.
        If the same key is seen again, the cached result is returned instead of re-executing the operation.
        """)

        st.warning("""
        ⚠️ **Without idempotency**: Network failures could cause duplicate web searches,
        multiple AI API calls for the same content, and duplicate file saves - leading to
        inconsistent results and unnecessary costs.
        """)

    # File information
    if metadata.get("file_saved"):
        st.info(f"📁 Research results saved to: `{metadata['file_saved']}`")

    # Add to history
    if result not in [item["result"] for item in SessionStateManager.get_research_history()]:
        query = extract_query_from_result(result)

        SessionStateManager.add_to_history(
            {
                "timestamp": datetime.now(),
                "query": query,
                "research_id": result.get("research_id", "unknown"),
                "result": result,
                "mcp_tx_stats": mcp_tx_stats,
            }
        )

    # Action button
    if st.button("🔄 Start New Research", type="primary"):
        return "new_research"

    return None


def render_sidebar() -> str | None:
    """Render sidebar with controls and history."""
    with st.sidebar:
        st.header("⚙️ Controls")

        # Auto-refresh toggle
        st.session_state.auto_refresh = st.toggle(
            "🔄 Auto-refresh Progress",
            value=st.session_state.get("auto_refresh", True),
            help="Automatically refresh progress every 2 seconds",
        )

        # Manual refresh button
        action = None
        if st.button("🔄 Refresh Now"):
            action = "refresh"

        # Clear current research
        if SessionStateManager.get_current_research_id() and st.button("🗑️ Clear Current"):
            action = "clear_current"

        st.divider()

        # Research History
        st.header("📚 Research History")

        history = SessionStateManager.get_research_history()
        if history:
            for i, item in enumerate(reversed(history)):
                with st.expander(f"🔬 {item['timestamp'].strftime('%H:%M')} - {item['query'][:30]}..."):
                    st.text(f"ID: {item['research_id']}")

                    metadata = item["result"].get("metadata", {})
                    st.text(f"Sources: {safe_get(metadata, 'sources_found')}")
                    st.text(f"MCP-Tx Success: {item['mcp_tx_stats'].get('reliability_rate', 'N/A')}")

                    if st.button(f"📄 View Report {i}", key=f"view_{i}"):
                        action = f"view_history_{i}"
        else:
            st.info("No research history yet.")

        st.divider()

        # About section
        st.header("📖 About")
        st.markdown("""
        **Smart Research Assistant** uses FastMCP-Tx to provide:

        - 🛡️ **Reliable Operations**: Automatic retry with exponential backoff
        - 🔄 **Idempotency**: Prevents duplicate processing
        - ✅ **ACK/NACK Tracking**: Confirms operation completion
        - 📊 **Real-time Progress**: Live updates on research status
        - 🔍 **Comprehensive Analysis**: Multi-step research workflow

        Built with Streamlit + FastMCP-Tx
        """)

        return action


# =============================================================================
# MAIN APPLICATION
# =============================================================================


def main():
    """Main application entry point."""
    try:
        # Initialize session state
        SessionStateManager.initialize()

        # Render header (includes page config)
        render_header()

        # Handle sidebar actions
        sidebar_action = render_sidebar()

        if sidebar_action:
            if sidebar_action == "refresh":
                st.rerun()
            elif sidebar_action == "clear_current":
                SessionStateManager.clear_current_research()
                st.rerun()
            elif sidebar_action.startswith("view_history_"):
                try:
                    history_index = int(sidebar_action.split("_")[-1])
                    history = SessionStateManager.get_research_history()
                    if 0 <= history_index < len(history):
                        history_item = list(reversed(history))[history_index]
                        SessionStateManager.clear_current_research()
                        st.session_state[SessionStateManager.VIEW_RESULT] = history_item["result"]
                        st.rerun()
                except (ValueError, IndexError):
                    st.error("Invalid history selection")

        # Main content area
        current_research_id = SessionStateManager.get_current_research_id()
        view_result = st.session_state.get(SessionStateManager.VIEW_RESULT)

        if view_result:
            # Viewing historical result
            st.header("📋 Previous Research Result")

            report_content = extract_report_content(view_result)
            if report_content:
                st.markdown(report_content)
            else:
                st.info("Report content not available")

            if st.button("🔄 Start New Research", type="primary"):
                if SessionStateManager.VIEW_RESULT in st.session_state:
                    del st.session_state[SessionStateManager.VIEW_RESULT]
                st.rerun()

        elif current_research_id:
            # Active research session
            should_continue_refresh = render_progress(current_research_id)

            results_action = render_results()
            if results_action == "new_research":
                SessionStateManager.clear_current_research()
                st.rerun()

            if should_continue_refresh:
                st.rerun()
        else:
            # No active research - show form
            research_id = render_research_form()
            if research_id:
                SessionStateManager.set_current_research_id(research_id)
                st.rerun()

        # Footer
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666;'>"
            "🔬 Smart Research Assistant powered by <strong>FastMCP-Tx</strong> • "
            "Built with ❤️ using Streamlit"
            "</div>",
            unsafe_allow_html=True,
        )

    except Exception as e:
        st.error("Application Error")
        st.error(f"An unexpected error occurred: {e!s}")


if __name__ == "__main__":
    main()
