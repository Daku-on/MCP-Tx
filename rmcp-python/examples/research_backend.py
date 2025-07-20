#!/usr/bin/env python3
"""
Research Backend - Streamlit-compatible wrapper for Smart Research Assistant

This module provides a Streamlit-compatible interface for the Smart Research Assistant,
enabling real-time progress tracking and session management in web frontend.
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock

from rmcp import FastRMCP, RetryPolicy, RMCPConfig

# Import the existing SmartResearchAssistant
from smart_research_assistant import SmartResearchAssistant, MockAIService


class ProgressTracker:
    """Thread-safe progress tracker for research operations."""
    
    def __init__(self):
        self.current_step = ""
        self.current_status = "ready"
        self.steps_completed = 0
        self.total_steps = 5
        self.progress_percentage = 0
        self.last_update = datetime.now()
        self.messages = []
        self.error = None
        self.result = None
        self.rmcp_stats = {}
        self._lock = threading.Lock()
    
    def update_step(self, step: str, status: str = "in_progress", message: str = ""):
        """Update current step progress."""
        with self._lock:
            self.current_step = step
            self.current_status = status
            if message:
                self.messages.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "step": step,
                    "message": message
                })
            self.last_update = datetime.now()
    
    def complete_step(self, step: str, message: str = ""):
        """Mark a step as completed."""
        with self._lock:
            self.steps_completed += 1
            self.progress_percentage = int((self.steps_completed / self.total_steps) * 100)
            if message:
                self.messages.append({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "step": step,
                    "message": f"✅ {message}"
                })
            self.last_update = datetime.now()
    
    def set_error(self, error: str):
        """Set error status."""
        with self._lock:
            self.error = error
            self.current_status = "error"
            self.messages.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": self.current_step,
                "message": f"❌ Error: {error}"
            })
    
    def set_complete(self, result: dict, rmcp_stats: dict):
        """Set completion status with results."""
        with self._lock:
            self.current_status = "completed"
            self.progress_percentage = 100
            self.result = result
            self.rmcp_stats = rmcp_stats
            self.messages.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "complete",
                "message": "🎉 Research completed successfully!"
            })
    
    def get_status(self) -> dict:
        """Get current status snapshot."""
        with self._lock:
            return {
                "current_step": self.current_step,
                "current_status": self.current_status,
                "steps_completed": self.steps_completed,
                "total_steps": self.total_steps,
                "progress_percentage": self.progress_percentage,
                "messages": self.messages.copy(),
                "error": self.error,
                "result": self.result,
                "rmcp_stats": self.rmcp_stats.copy(),
                "last_update": self.last_update
            }


class StreamlitResearchAssistant:
    """
    Streamlit-compatible wrapper for SmartResearchAssistant.
    
    Provides async research capabilities with real-time progress tracking
    suitable for web frontend integration.
    """
    
    def __init__(self):
        self.progress_tracker = None
        self.research_thread = None
        self.research_assistant = None
        self.research_app = None
    
    def start_research(self, query: str, research_id: str = None) -> str:
        """
        Start research in background thread with progress tracking.
        
        Args:
            query: Research query
            research_id: Optional research session ID
            
        Returns:
            Research ID for tracking
        """
        if not research_id:
            research_id = f"research_{int(datetime.now().timestamp())}"
        
        # Create new progress tracker
        self.progress_tracker = ProgressTracker()
        
        # Start research in background thread
        self.research_thread = threading.Thread(
            target=self._run_research_async,
            args=(query, research_id),
            daemon=True
        )
        self.research_thread.start()
        
        return research_id
    
    def get_progress(self) -> dict:
        """Get current research progress."""
        if self.progress_tracker:
            return self.progress_tracker.get_status()
        return {"current_status": "ready"}
    
    def is_research_active(self) -> bool:
        """Check if research is currently running."""
        return (
            self.research_thread and 
            self.research_thread.is_alive() and
            self.progress_tracker and 
            self.progress_tracker.current_status in ["in_progress", "running"]
        )
    
    def _run_research_async(self, query: str, research_id: str):
        """Run research in async context within thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the research
            loop.run_until_complete(self._conduct_research_with_tracking(query, research_id))
            
        except Exception as e:
            if self.progress_tracker:
                self.progress_tracker.set_error(str(e))
        finally:
            loop.close()
    
    async def _conduct_research_with_tracking(self, query: str, research_id: str):
        """Conduct research with detailed progress tracking."""
        self.progress_tracker.update_step("initialization", "running", "Initializing research session...")
        
        try:
            # Setup FastRMCP
            mock_mcp_session = AsyncMock()
            config = RMCPConfig(
                default_timeout_ms=30000,
                max_concurrent_requests=5,
                enable_request_logging=True,
                deduplication_window_ms=600000
            )
            
            self.research_app = FastRMCP(
                mock_mcp_session,
                config=config,
                name="StreamlitResearchAssistant"
            )
            
            async with self.research_app:
                # Initialize research assistant
                self.research_assistant = SmartResearchAssistant(self.research_app)
                await self.research_assistant.setup_tools()
                
                self.progress_tracker.complete_step("initialization", "Research tools initialized")
                
                # Step 1: Web Search
                self.progress_tracker.update_step("web_search", "running", f"Searching for: {query}")
                
                search_result = await self.research_app.call_tool(
                    "web_search",
                    {"query": query, "num_results": 6},
                    idempotency_key=f"search-{research_id}"
                )
                
                search_data = search_result.result
                self.progress_tracker.complete_step(
                    "web_search", 
                    f"Found {search_data['total_found']} sources"
                )
                
                # Step 2: Content Analysis
                self.progress_tracker.update_step("content_analysis", "running", "Analyzing content...")
                
                analyses = []
                for i, source in enumerate(search_data["results"][:3]):
                    self.progress_tracker.update_step(
                        "content_analysis", 
                        "running", 
                        f"Analyzing source {i+1}/3: {source['title']}"
                    )
                    
                    try:
                        analysis_result = await self.research_app.call_tool(
                            "analyze_content",
                            {"content": f"Title: {source['title']}\n\nContent: {source['snippet']}"},
                            idempotency_key=f"analyze-{research_id}-{i}"
                        )
                        analyses.append(analysis_result.result)
                    except Exception as e:
                        self.progress_tracker.update_step(
                            "content_analysis",
                            "running",
                            f"⚠️ Analysis failed for source {i+1}: {e}"
                        )
                
                self.progress_tracker.complete_step(
                    "content_analysis",
                    f"Completed {len(analyses)} content analyses"
                )
                
                # Step 3: Fact Checking
                self.progress_tracker.update_step("fact_checking", "running", "Fact checking claims...")
                
                fact_checks = []
                for i, analysis in enumerate(analyses[:2]):
                    self.progress_tracker.update_step(
                        "fact_checking",
                        "running",
                        f"Fact checking claim {i+1}/2"
                    )
                    
                    try:
                        claim = analysis["analysis"][:300]
                        fact_check_result = await self.research_app.call_tool(
                            "fact_check",
                            {
                                "claim": claim,
                                "sources": [s["url"] for s in search_data["results"][:3]]
                            },
                            idempotency_key=f"factcheck-{research_id}-{i}"
                        )
                        fact_checks.append(fact_check_result.result)
                    except Exception as e:
                        self.progress_tracker.update_step(
                            "fact_checking",
                            "running",
                            f"⚠️ Fact check failed for claim {i+1}: {e}"
                        )
                
                self.progress_tracker.complete_step(
                    "fact_checking",
                    f"Completed {len(fact_checks)} fact checks"
                )
                
                # Step 4: Report Generation
                self.progress_tracker.update_step("report_generation", "running", "Generating research report...")
                
                report_result = await self.research_app.call_tool(
                    "generate_research_report",
                    {
                        "research_id": research_id,
                        "search_results": search_data["results"],
                        "analyses": analyses,
                        "fact_checks": fact_checks,
                        "query": query
                    },
                    idempotency_key=f"report-{research_id}"
                )
                
                report = report_result.result
                self.progress_tracker.complete_step("report_generation", "Research report generated")
                
                # Step 5: Save Results
                self.progress_tracker.update_step("save_results", "running", "Saving research results...")
                
                save_result = await self.research_app.call_tool(
                    "save_research",
                    {
                        "research_id": research_id,
                        "report": report
                    },
                    idempotency_key=f"save-{research_id}"
                )
                
                self.progress_tracker.complete_step("save_results", "Results saved successfully")
                
                # Calculate RMCP statistics
                steps = self.research_assistant.research_sessions[research_id]["steps"]
                total_attempts = sum(step["attempts"] for step in steps)
                successful_steps = sum(1 for step in steps if step["ack"])
                
                result = {
                    "research_id": research_id,
                    "status": "success",
                    "report": report,
                    "metadata": {
                        "sources_found": len(search_data["results"]),
                        "analyses_completed": len(analyses),
                        "fact_checks_performed": len(fact_checks),
                        "file_saved": save_result.result["saved_to"]
                    }
                }
                
                rmcp_stats = {
                    "total_rmcp_attempts": total_attempts,
                    "successful_steps": successful_steps,
                    "reliability_rate": f"{(successful_steps/len(steps)*100):.1f}%" if steps else "0%",
                    "steps_details": steps
                }
                
                # Set completion
                self.progress_tracker.set_complete(result, rmcp_stats)
                
        except Exception as e:
            self.progress_tracker.set_error(str(e))
            raise


# Global research assistant instance for Streamlit
research_assistant = StreamlitResearchAssistant()