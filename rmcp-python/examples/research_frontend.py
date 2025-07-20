#!/usr/bin/env python3
"""
Smart Research Assistant - Streamlit Frontend

A modern web interface for the Smart Research Assistant powered by FastRMCP.
Features real-time progress tracking, interactive results visualization,
and comprehensive RMCP reliability metrics.

Usage:
    streamlit run research_frontend.py
"""

import streamlit as st
import time
import json
from datetime import datetime
from research_backend import research_assistant


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "research_history" not in st.session_state:
        st.session_state.research_history = []
    if "current_research_id" not in st.session_state:
        st.session_state.current_research_id = None
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = True


def display_header():
    """Display application header and branding."""
    st.set_page_config(
        page_title="Smart Research Assistant",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔬 Smart Research Assistant")
        st.markdown("*Powered by FastRMCP for Reliable AI Research*")
        
        st.markdown("""
        <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">
            <p style="color: white; margin: 0; text-align: center;">
                <strong>🛡️ RMCP Reliability Features:</strong> 
                Automatic Retry • Idempotency • ACK/NACK Tracking • Error Recovery
            </p>
        </div>
        """, unsafe_allow_html=True)


def display_research_form():
    """Display the main research input form."""
    st.header("🔍 Start New Research")
    
    with st.form("research_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Research Query",
                placeholder="Enter your research question (e.g., 'AI impact on software development 2024')",
                help="Describe what you want to research. The assistant will search, analyze, and fact-check information."
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            submit_button = st.form_submit_button(
                "🚀 Start Research",
                type="primary",
                use_container_width=True
            )
        
        # Advanced options
        with st.expander("⚙️ Advanced Options"):
            col1, col2 = st.columns(2)
            with col1:
                custom_id = st.text_input(
                    "Custom Research ID (Optional)",
                    placeholder="research_custom_001"
                )
            with col2:
                st.markdown("**Research will include:**")
                st.markdown("- 🔍 Web search (6 sources)")
                st.markdown("- 📊 Content analysis (3 sources)")
                st.markdown("- ✅ Fact checking (2 claims)")
                st.markdown("- 📄 Report generation")
                st.markdown("- 💾 Persistent storage")
        
        if submit_button and query:
            if research_assistant.is_research_active():
                st.error("⚠️ Research already in progress. Please wait for completion.")
            else:
                research_id = research_assistant.start_research(
                    query,
                    custom_id if custom_id else None
                )
                st.session_state.current_research_id = research_id
                st.success(f"✅ Research started! ID: {research_id}")
                st.rerun()
        elif submit_button:
            st.error("Please enter a research query.")


def display_progress_section():
    """Display real-time research progress."""
    if not st.session_state.current_research_id:
        return
    
    progress_data = research_assistant.get_progress()
    
    if progress_data["current_status"] == "ready":
        return
    
    st.header("📊 Research Progress")
    
    # Progress overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Status",
            progress_data["current_status"].title(),
            delta=progress_data["current_step"].replace("_", " ").title() if progress_data["current_step"] else None
        )
    
    with col2:
        st.metric(
            "Progress",
            f"{progress_data['progress_percentage']}%",
            delta=f"{progress_data['steps_completed']}/{progress_data['total_steps']} steps"
        )
    
    with col3:
        if progress_data.get("rmcp_stats"):
            st.metric(
                "RMCP Reliability",
                progress_data["rmcp_stats"].get("reliability_rate", "N/A"),
                delta=f"{progress_data['rmcp_stats'].get('successful_steps', 0)} successful steps"
            )
        else:
            st.metric("RMCP Reliability", "Calculating...", delta="In progress")
    
    with col4:
        st.metric(
            "Last Update",
            progress_data["last_update"].strftime("%H:%M:%S") if progress_data.get("last_update") else "N/A"
        )
    
    # Progress bar
    progress_bar = st.progress(progress_data["progress_percentage"] / 100)
    
    # Current step indicator
    step_names = {
        "initialization": "🔧 Initialization",
        "web_search": "🔍 Web Search",
        "content_analysis": "📊 Content Analysis", 
        "fact_checking": "✅ Fact Checking",
        "report_generation": "📄 Report Generation",
        "save_results": "💾 Save Results"
    }
    
    if progress_data["current_step"] in step_names:
        st.info(f"**Current Step:** {step_names[progress_data['current_step']]}")
    
    # Real-time messages
    if progress_data.get("messages"):
        with st.expander("📝 Detailed Progress Log", expanded=True):
            message_container = st.container()
            with message_container:
                for message in progress_data["messages"][-10:]:  # Show last 10 messages
                    st.text(f"[{message['timestamp']}] {message['step']}: {message['message']}")
    
    # Error display
    if progress_data.get("error"):
        st.error(f"❌ Error: {progress_data['error']}")
    
    # Auto-refresh
    if st.session_state.auto_refresh and progress_data["current_status"] in ["running", "in_progress"]:
        time.sleep(2)
        st.rerun()


def display_results_section():
    """Display research results and RMCP statistics."""
    progress_data = research_assistant.get_progress()
    
    if progress_data["current_status"] != "completed" or not progress_data.get("result"):
        return
    
    result = progress_data["result"]
    rmcp_stats = progress_data["rmcp_stats"]
    
    st.header("📋 Research Results")
    
    # Results overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Sources Found",
            result["metadata"]["sources_found"]
        )
    
    with col2:
        st.metric(
            "Analyses Completed",
            result["metadata"]["analyses_completed"]
        )
    
    with col3:
        st.metric(
            "Fact Checks",
            result["metadata"]["fact_checks_performed"]
        )
    
    # Research Report
    st.subheader("📄 Research Report")
    
    if result.get("report", {}).get("content"):
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📖 Formatted Report", "🔧 Raw Content"])
        
        with tab1:
            # Display formatted report
            st.markdown(result["report"]["content"])
        
        with tab2:
            # Display raw JSON
            st.json(result["report"])
    
    # RMCP Reliability Metrics
    st.subheader("🛡️ RMCP Reliability Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Attempts",
            rmcp_stats.get("total_rmcp_attempts", 0),
            help="Total number of RMCP request attempts across all steps"
        )
    
    with col2:
        st.metric(
            "Success Rate",
            rmcp_stats.get("reliability_rate", "0%"),
            help="Percentage of successful RMCP operations"
        )
    
    with col3:
        st.metric(
            "Successful Steps",
            rmcp_stats.get("successful_steps", 0),
            help="Number of research steps completed successfully"
        )
    
    # RMCP Step Details
    if rmcp_stats.get("steps_details"):
        with st.expander("🔍 RMCP Step Details", expanded=False):
            for step in rmcp_stats["steps_details"]:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.text(f"Step: {step['step']}")
                
                with col2:
                    st.text(f"Attempts: {step['attempts']}")
                
                with col3:
                    status = "✅ ACK" if step['ack'] else "❌ NACK"
                    st.text(f"Status: {status}")
                
                with col4:
                    duplicate = "🔄 Duplicate" if step['duplicate'] else "🆕 New"
                    st.text(f"Type: {duplicate}")
                
                st.divider()
    
    # File download
    if result["metadata"].get("file_saved"):
        st.info(f"📁 Research results saved to: `{result['metadata']['file_saved']}`")
    
    # Add to history
    if result not in [item["result"] for item in st.session_state.research_history]:
        st.session_state.research_history.append({
            "timestamp": datetime.now(),
            "query": result["report"]["query"],
            "research_id": result["research_id"],
            "result": result,
            "rmcp_stats": rmcp_stats
        })
    
    # Option to start new research
    if st.button("🔄 Start New Research", type="primary"):
        st.session_state.current_research_id = None
        st.rerun()


def display_sidebar():
    """Display sidebar with controls and history."""
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Auto-refresh toggle
        st.session_state.auto_refresh = st.toggle(
            "🔄 Auto-refresh Progress",
            value=st.session_state.auto_refresh,
            help="Automatically refresh progress every 2 seconds"
        )
        
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        # Clear current research
        if st.session_state.current_research_id and st.button("🗑️ Clear Current"):
            st.session_state.current_research_id = None
            st.rerun()
        
        st.divider()
        
        # Research History
        st.header("📚 Research History")
        
        if st.session_state.research_history:
            for i, item in enumerate(reversed(st.session_state.research_history)):
                with st.expander(f"🔬 {item['timestamp'].strftime('%H:%M')} - {item['query'][:30]}..."):
                    st.text(f"ID: {item['research_id']}")
                    st.text(f"Sources: {item['result']['metadata']['sources_found']}")
                    st.text(f"RMCP Success: {item['rmcp_stats'].get('reliability_rate', 'N/A')}")
                    
                    if st.button(f"📄 View Report {i}", key=f"view_{i}"):
                        st.session_state.current_research_id = item['research_id']
                        # Update progress tracker with historical data
                        research_assistant.progress_tracker = type('ProgressTracker', (), {
                            'get_status': lambda: {
                                **item,
                                'current_status': 'completed',
                                'progress_percentage': 100,
                                'current_step': 'completed',
                                'messages': []
                            }
                        })()
                        st.rerun()
        else:
            st.info("No research history yet.")
        
        st.divider()
        
        # About section
        st.header("ℹ️ About")
        st.markdown("""
        **Smart Research Assistant** uses FastRMCP to provide:
        
        - 🛡️ **Reliable Operations**: Automatic retry with exponential backoff
        - 🔄 **Idempotency**: Prevents duplicate processing
        - ✅ **ACK/NACK Tracking**: Confirms operation completion
        - 📊 **Real-time Progress**: Live updates on research status
        - 🔍 **Comprehensive Analysis**: Multi-step research workflow
        
        Built with Streamlit + FastRMCP
        """)


def main():
    """Main application entry point."""
    init_session_state()
    display_header()
    display_sidebar()
    
    # Main content area
    display_research_form()
    display_progress_section()
    display_results_section()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "🔬 Smart Research Assistant powered by <strong>FastRMCP</strong> • "
        "Built with ❤️ using Streamlit"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()