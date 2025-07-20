#!/usr/bin/env python3
"""
Research Backend (Consolidated) - Complete research system in a single file

This consolidated version includes all research functionality:
- Research step classes
- Retry utilities
- Progress tracking
- Main research orchestration

All in one file for simplicity and easier deployment.
"""

import asyncio
import json
import logging
import os
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

from real_ai_service import RealAIService

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("research_backend_consolidated.log")],
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# RETRY UTILITIES
# =============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry operations."""

    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    operation_name: str = "operation"


@dataclass
class RetryResult:
    """Result of a retry operation."""

    success: bool
    result: Any = None
    attempts_made: int = 0
    total_delay: float = 0.0
    last_error: Exception | None = None


class RetryableOperation:
    """Helper class for executing operations with retry logic."""

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute(
        self, operation: Callable[[], Any], progress_callback: Callable[[int, int, str], None] | None = None
    ) -> RetryResult:
        """Execute an operation with retry logic."""
        last_error = None
        total_delay = 0.0

        logger.info(f"🚀 Starting {self.config.operation_name}")

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.info(f"   🔄 Attempt {attempt}/{self.config.max_attempts}")

                if progress_callback:
                    progress_callback(attempt, self.config.max_attempts, f"Attempting {self.config.operation_name}")

                result = await operation()

                logger.info(f"✅ {self.config.operation_name} SUCCESS - Attempt: {attempt}")
                return RetryResult(success=True, result=result, attempts_made=attempt, total_delay=total_delay)

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ {self.config.operation_name} attempt {attempt} failed: {e!s}")

                if attempt == self.config.max_attempts:
                    logger.error(f"❌ All {self.config.operation_name} attempts failed")
                    break

                delay = min(
                    self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1)), self.config.max_delay
                )
                total_delay += delay

                logger.info(f"   ⏱️ Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)

        return RetryResult(
            success=False,
            result=None,
            attempts_made=self.config.max_attempts,
            total_delay=total_delay,
            last_error=last_error,
        )


class RetryConfigs:
    """Standard retry configurations for different operation types."""

    WEB_SEARCH = RetryConfig(max_attempts=3, base_delay=2.0, backoff_multiplier=2.0, operation_name="web_search")
    CONTENT_ANALYSIS = RetryConfig(
        max_attempts=5, base_delay=1.0, backoff_multiplier=1.5, operation_name="content_analysis"
    )
    FACT_CHECKING = RetryConfig(max_attempts=3, base_delay=1.5, backoff_multiplier=2.0, operation_name="fact_checking")
    REPORT_GENERATION = RetryConfig(
        max_attempts=2, base_delay=2.0, backoff_multiplier=2.0, operation_name="report_generation"
    )
    FILE_OPERATIONS = RetryConfig(
        max_attempts=2, base_delay=0.5, backoff_multiplier=2.0, operation_name="file_operations"
    )


async def retry_operation(
    operation: Callable[[], Any], config: RetryConfig, progress_callback: Callable[[int, int, str], None] | None = None
) -> RetryResult:
    """Convenience function for retrying operations."""
    retryable = RetryableOperation(config)
    return await retryable.execute(operation, progress_callback)


# =============================================================================
# RESEARCH STEPS
# =============================================================================


class ResearchStepBase:
    """Base class for all research steps."""

    def __init__(self, ai_service: RealAIService, research_id: str):
        self.ai_service = ai_service
        self.research_id = research_id

    async def execute(self, progress_callback=None) -> dict[str, Any]:
        """Execute the research step. Must be implemented by subclasses."""
        raise NotImplementedError


class WebSearchStep(ResearchStepBase):
    """Handles web search with retry logic and source validation."""

    async def execute(self, query: str, num_results: int = 6, progress_callback=None) -> dict[str, Any]:
        """Execute web search with retry logic."""

        async def search_operation():
            return await self.ai_service.search_web(query, num_results)

        result = await retry_operation(search_operation, RetryConfigs.WEB_SEARCH, progress_callback)

        if not result.success:
            raise result.last_error or Exception("Web search failed")

        search_data = result.result

        return {
            "search_data": search_data,
            "attempts": result.attempts_made,
            "query": query,
            "sources_found": search_data.get("total_found", 0),
            "metadata": {
                "search_engine": search_data.get("search_engine", "Unknown"),
                "retry_attempts": result.attempts_made,
                "total_delay": result.total_delay,
            },
        }


class ContentAnalysisStep(ResearchStepBase):
    """Handles content analysis of sources with individual retry logic."""

    async def execute(self, search_results: list[dict], max_sources: int = 3, progress_callback=None) -> dict[str, Any]:
        """Execute content analysis on search results."""
        analyses = []
        total_attempts = 0

        for i, source in enumerate(search_results[:max_sources]):
            if progress_callback:
                progress_callback(i + 1, max_sources, f"Analyzing source: {source.get('title', 'Unknown')}")

            content = f"Title: {source.get('title', 'N/A')}\n\nContent: {source.get('snippet', 'N/A')}"

            async def analysis_operation():
                analysis_text = await self.ai_service.analyze_content(content)
                return {
                    "original_length": len(content),
                    "analysis": analysis_text,
                    "processed_at": datetime.utcnow().isoformat(),
                    "source_title": source.get("title", "N/A"),
                    "source_url": source.get("url", "N/A"),
                }

            try:
                result = await retry_operation(analysis_operation, RetryConfigs.CONTENT_ANALYSIS)

                if result.success:
                    analyses.append(result.result)
                    total_attempts += result.attempts_made

            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, max_sources, f"Error analyzing source {i + 1}: {e!s}")

        return {
            "analyses": analyses,
            "total_attempts": total_attempts,
            "sources_analyzed": len(analyses),
            "sources_requested": max_sources,
            "metadata": {
                "success_rate": len(analyses) / max_sources if max_sources > 0 else 0,
                "total_retry_attempts": total_attempts,
            },
        }


class FactCheckingStep(ResearchStepBase):
    """Handles fact-checking of analysis results."""

    async def execute(
        self, analyses: list[dict], sources: list[str], max_checks: int = 2, progress_callback=None
    ) -> dict[str, Any]:
        """Execute fact-checking on analysis results."""
        fact_checks = []
        total_attempts = 0

        for i, analysis in enumerate(analyses[:max_checks]):
            if progress_callback:
                progress_callback(i + 1, max_checks, f"Fact-checking claim {i + 1}")

            claim = analysis.get("analysis", "")[:300]  # First 300 chars

            async def fact_check_operation():
                verification_text = await self.ai_service.fact_check(claim, sources)
                return {
                    "claim": claim,
                    "verification": verification_text,
                    "sources_checked": len(sources),
                    "checked_at": datetime.utcnow().isoformat(),
                    "source_analysis": analysis.get("source_title", "N/A"),
                }

            try:
                result = await retry_operation(fact_check_operation, RetryConfigs.FACT_CHECKING)

                if result.success:
                    fact_checks.append(result.result)
                    total_attempts += result.attempts_made

            except Exception as e:
                if progress_callback:
                    progress_callback(i + 1, max_checks, f"Error fact-checking claim {i + 1}: {e!s}")

        return {
            "fact_checks": fact_checks,
            "total_attempts": total_attempts,
            "checks_completed": len(fact_checks),
            "checks_requested": max_checks,
            "metadata": {
                "success_rate": len(fact_checks) / max_checks if max_checks > 0 else 0,
                "total_retry_attempts": total_attempts,
            },
        }


class ReportGenerationStep(ResearchStepBase):
    """Handles research report generation."""

    async def execute(
        self, query: str, search_data: dict, analyses: list[dict], fact_checks: list[dict], progress_callback=None
    ) -> dict[str, Any]:
        """Execute report generation."""
        if progress_callback:
            progress_callback(1, 1, "Generating comprehensive research report")

        async def report_operation():
            report_data = {
                "query": query,
                "sources_count": len(search_data.get("results", [])),
                "analyses_count": len(analyses),
                "fact_checks_count": len(fact_checks),
                "search_results": search_data.get("results", []),
                "analyses": analyses,
                "fact_checks": fact_checks,
            }

            report_content = await self.ai_service.generate_report(report_data)

            return {
                "research_id": self.research_id,
                "report": report_content,
                "generated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "sources_analyzed": len(search_data.get("results", [])),
                    "content_analyses": len(analyses),
                    "fact_checks_performed": len(fact_checks),
                    "query": query,
                },
            }

        result = await retry_operation(report_operation, RetryConfigs.REPORT_GENERATION, progress_callback)

        if not result.success:
            raise result.last_error or Exception("Report generation failed")

        report_data = result.result
        report_data["generation_attempts"] = result.attempts_made

        return report_data


class SaveResultsStep(ResearchStepBase):
    """Handles saving research results to persistent storage."""

    async def execute(
        self, report: dict[str, Any], results_dir: str = "research_results", progress_callback=None
    ) -> dict[str, Any]:
        """Execute result saving."""
        if progress_callback:
            progress_callback(1, 1, f"Saving research results to {results_dir}")

        async def save_operation():
            # Create results directory if it doesn't exist
            os.makedirs(results_dir, exist_ok=True)

            # Save to JSON file
            filename = f"{self.research_id}.json"
            filepath = os.path.join(results_dir, filename)

            save_data = {
                "research_id": self.research_id,
                "report": report,
                "saved_at": datetime.utcnow().isoformat(),
                "file_version": "1.0",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            return {
                "research_id": self.research_id,
                "saved_to": filepath,
                "file_size": os.path.getsize(filepath),
                "saved_at": datetime.utcnow().isoformat(),
                "results_directory": results_dir,
            }

        result = await retry_operation(save_operation, RetryConfigs.FILE_OPERATIONS, progress_callback)

        if not result.success:
            raise result.last_error or Exception("Failed to save results")

        save_data = result.result
        save_data["save_attempts"] = result.attempts_made

        return save_data


class ResearchStatistics:
    """Tracks and calculates statistics for research operations."""

    def __init__(self):
        self.step_stats = {}
        self.total_attempts = 0
        self.successful_steps = 0
        self.total_steps = 0

    def add_step_result(self, step_name: str, attempts: int, success: bool, **metadata):
        """Add statistics for a completed step."""
        self.step_stats[step_name] = {"attempts": attempts, "success": success, "metadata": metadata}
        self.total_attempts += attempts
        if success:
            self.successful_steps += 1
        self.total_steps += 1

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics."""
        reliability_rate = (self.successful_steps / self.total_steps * 100) if self.total_steps > 0 else 0

        return {
            "total_mcp_tx_attempts": self.total_attempts,
            "successful_operations": self.successful_steps,
            "total_operations": self.total_steps,
            "reliability_rate": f"{reliability_rate:.1f}%",
            "operation_details": self.step_stats.copy(),
        }

    def get_detailed_stats(self) -> dict[str, Any]:
        """Get detailed statistics with step-by-step breakdown."""
        summary = self.get_summary()
        summary["steps_details"] = [
            {
                "step": step_name,
                "attempts": stats["attempts"],
                "ack": stats["success"],
                "duplicate": False,  # For compatibility with existing frontend
                **stats["metadata"],
            }
            for step_name, stats in self.step_stats.items()
        ]
        return summary


# =============================================================================
# PROGRESS TRACKING
# =============================================================================


class ProgressTracker:
    """Thread-safe progress tracker for research operations."""

    def __init__(self):
        self.current_step = ""
        self.current_status = "ready"
        self.steps_completed = 0
        self.total_steps = 6  # initialization + 5 main steps
        self.progress_percentage = 0
        self.last_update = datetime.now()
        self.messages = []
        self.error = None
        self.result = None
        self.mcp_tx_stats = {}
        self.completed_steps = set()
        self._lock = threading.Lock()

    def update_step(self, step: str, status: str = "in_progress", message: str = ""):
        """Update current step progress."""
        with self._lock:
            self.current_step = step
            self.current_status = status
            if message:
                self.messages.append(
                    {"timestamp": datetime.now().strftime("%H:%M:%S"), "step": step, "message": message}
                )
                logger.info(f"Progress Update - Step: {step}, Status: {status}, Message: {message}")
            self.last_update = datetime.now()
            self.progress_percentage = min(self.progress_percentage, 100)

    def complete_step(self, step: str, message: str = ""):
        """Mark a step as completed."""
        with self._lock:
            if step not in self.completed_steps:
                self.steps_completed += 1
                self.completed_steps.add(step)
                self.progress_percentage = min(int((self.steps_completed / self.total_steps) * 100), 100)
                logger.info(f"Step Completed ({self.steps_completed}/{self.total_steps}) - {step}: {message}")
            else:
                logger.warning(f"Step '{step}' already completed - skipping duplicate completion")

            if message:
                self.messages.append(
                    {"timestamp": datetime.now().strftime("%H:%M:%S"), "step": step, "message": f"✅ {message}"}
                )
            self.last_update = datetime.now()

    def set_error(self, error: str):
        """Set error status."""
        with self._lock:
            self.error = error
            self.current_status = "error"
            self.messages.append(
                {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "step": self.current_step,
                    "message": f"❌ Error: {error}",
                }
            )
            logger.error(f"Research Error - Step: {self.current_step}, Error: {error}")
            logger.error(f"Full traceback: {traceback.format_exc()}")

    def set_complete(self, result: dict[str, Any], mcp_tx_stats: dict[str, Any]):
        """Set completion status with results."""
        with self._lock:
            self.current_status = "completed"
            self.progress_percentage = 100
            self.result = result
            self.mcp_tx_stats = mcp_tx_stats
            self.messages.append(
                {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "step": "complete",
                    "message": "🎉 Research completed successfully!",
                }
            )
            logger.info(f"Research Completed Successfully - ID: {result.get('research_id', 'unknown')}")
            logger.info(f"Statistics: {mcp_tx_stats}")

    def get_status(self) -> dict[str, Any]:
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
                "mcp_tx_stats": self.mcp_tx_stats.copy(),
                "last_update": self.last_update,
            }


# =============================================================================
# MAIN RESEARCH ASSISTANT
# =============================================================================


class StreamlitResearchAssistant:
    """Main research assistant with modular step execution."""

    def __init__(self):
        self.progress_tracker = None
        self.research_thread = None
        self.ai_service = None

    def start_research(self, query: str, research_id: str | None = None) -> str:
        """Start research in background thread with progress tracking."""
        if not research_id:
            research_id = f"research_{int(datetime.now().timestamp())}"

        logger.info(f"Starting research session - ID: {research_id}, Query: {query}")

        # Create new progress tracker
        self.progress_tracker = ProgressTracker()

        # Start research in background thread
        self.research_thread = threading.Thread(target=self._run_research_async, args=(query, research_id), daemon=True)
        self.research_thread.start()

        logger.info(f"Research thread started for ID: {research_id}")
        return research_id

    def get_progress(self) -> dict[str, Any]:
        """Get current research progress."""
        if self.progress_tracker:
            return self.progress_tracker.get_status()
        return {"current_status": "ready"}

    def is_research_active(self) -> bool:
        """Check if research is currently running."""
        return (
            self.research_thread
            and self.research_thread.is_alive()
            and self.progress_tracker
            and self.progress_tracker.current_status in ["in_progress", "running"]
        )

    def _run_research_async(self, query: str, research_id: str):
        """Run research in async context within thread."""
        try:
            logger.info(f"Setting up async loop for research ID: {research_id}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            logger.info(f"Starting research execution for ID: {research_id}")
            loop.run_until_complete(self._conduct_research(query, research_id))

        except Exception as e:
            logger.error(f"Critical error in research thread for ID: {research_id}: {e!s}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if self.progress_tracker:
                self.progress_tracker.set_error(str(e))
        finally:
            logger.info(f"Closing async loop for research ID: {research_id}")
            loop.close()

    async def _conduct_research(self, query: str, research_id: str):
        """Conduct research using modular step classes."""
        logger.info(f"Starting modular research for ID: {research_id}")
        self.progress_tracker.update_step("initialization", "running", "Initializing research session...")

        try:
            # Initialize AI service and statistics
            self.ai_service = RealAIService()
            stats = ResearchStatistics()

            logger.info("AI service initialized successfully")
            self.progress_tracker.complete_step("initialization", "Research tools initialized")

            # Create progress callback
            def progress_callback(attempt: int, max_attempts: int, message: str):
                self.progress_tracker.update_step(
                    self.progress_tracker.current_step, "running", f"{message} (attempt {attempt}/{max_attempts})"
                )

            # Step 1: Web Search
            self.progress_tracker.update_step("web_search", "running", f"Searching for: {query}")

            search_step = WebSearchStep(self.ai_service, research_id)
            search_result = await search_step.execute(query, 6, progress_callback)

            stats.add_step_result(
                "web_search", search_result["attempts"], True, sources_found=search_result["sources_found"]
            )

            self.progress_tracker.complete_step(
                "web_search", f"Found {search_result['sources_found']} sources (attempts: {search_result['attempts']})"
            )

            # Step 2: Content Analysis
            self.progress_tracker.update_step("content_analysis", "running", "Analyzing content...")

            analysis_step = ContentAnalysisStep(self.ai_service, research_id)
            analysis_result = await analysis_step.execute(search_result["search_data"]["results"], 3, progress_callback)

            stats.add_step_result(
                "content_analysis",
                analysis_result["total_attempts"],
                True,
                completed=analysis_result["sources_analyzed"],
            )

            self.progress_tracker.complete_step(
                "content_analysis",
                f"Completed {analysis_result['sources_analyzed']} analyses (attempts: {analysis_result['total_attempts']})",
            )

            # Step 3: Fact Checking
            self.progress_tracker.update_step("fact_checking", "running", "Fact checking claims...")

            sources = [s["url"] for s in search_result["search_data"]["results"][:3]]
            fact_check_step = FactCheckingStep(self.ai_service, research_id)
            fact_check_result = await fact_check_step.execute(
                analysis_result["analyses"], sources, 2, progress_callback
            )

            stats.add_step_result(
                "fact_checking",
                fact_check_result["total_attempts"],
                True,
                completed=fact_check_result["checks_completed"],
            )

            self.progress_tracker.complete_step(
                "fact_checking",
                f"Completed {fact_check_result['checks_completed']} fact checks (attempts: {fact_check_result['total_attempts']})",
            )

            # Step 4: Report Generation
            self.progress_tracker.update_step("report_generation", "running", "Generating research report...")

            report_step = ReportGenerationStep(self.ai_service, research_id)
            report_result = await report_step.execute(
                query,
                search_result["search_data"],
                analysis_result["analyses"],
                fact_check_result["fact_checks"],
                progress_callback,
            )

            stats.add_step_result("report_generation", report_result["generation_attempts"], True)

            self.progress_tracker.complete_step(
                "report_generation", f"Report generated (attempts: {report_result['generation_attempts']})"
            )

            # Step 5: Save Results
            self.progress_tracker.update_step("save_results", "running", "Saving research results...")

            save_step = SaveResultsStep(self.ai_service, research_id)
            save_result = await save_step.execute(report_result, progress_callback=progress_callback)

            stats.add_step_result("save_results", save_result["save_attempts"], True)

            self.progress_tracker.complete_step(
                "save_results", f"Results saved (attempts: {save_result['save_attempts']})"
            )

            # Generate final result and statistics
            final_result = {
                "research_id": research_id,
                "status": "success",
                "report": report_result,
                "metadata": {
                    "sources_found": search_result["sources_found"],
                    "analyses_completed": analysis_result["sources_analyzed"],
                    "fact_checks_performed": fact_check_result["checks_completed"],
                    "file_saved": save_result["saved_to"],
                },
            }

            final_stats = stats.get_detailed_stats()

            # Log completion
            logger.info("✅ Modular Research Session Completed Successfully!")
            logger.info(f"   Research ID: {research_id}")
            logger.info(f"   Total Operations: {stats.total_steps}")
            logger.info(f"   Total Retry Attempts: {stats.total_attempts}")
            logger.info(f"   Success Rate: {final_stats['reliability_rate']}")

            # Set completion
            self.progress_tracker.set_complete(final_result, final_stats)

        except Exception as e:
            logger.error(f"Research failed for ID: {research_id}: {e!s}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.progress_tracker.set_error(str(e))
            raise


# Global research assistant instance for Streamlit
research_assistant = StreamlitResearchAssistant()
