"""Multi-Agent Research Backend using MCP-Tx with real AI services."""

import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import anyio
import streamlit as st
from dotenv import load_dotenv
from openai import AsyncOpenAI
from serpapi import GoogleSearch  # type: ignore

from mcp_tx import FastMCPTx, MCPTxConfig, MCPTxError, RetryPolicy

# --- Configuration ---
# Load .env file from the same directory as this script
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- API Client Initialization ---
openai_client: AsyncOpenAI | None = None
serpapi_key: str | None = None
try:
    openai_api_key = os.environ["OPENAI_API_KEY"]
    if openai_api_key:
        openai_client = AsyncOpenAI(api_key=openai_api_key)
    else:
        logger.error("CRITICAL: OPENAI_API_KEY is set but empty. Please check your .env file.")

    serpapi_key = os.environ.get("SERPAPI_KEY")
    if not serpapi_key:
        logger.warning("SERPAPI_KEY not found. Web search functionality will be limited.")
except KeyError:
    logger.error("CRITICAL: Missing environment variable OPENAI_API_KEY. Please check your .env file.")


# MCP-Tx Configuration
config = MCPTxConfig(
    default_timeout_ms=300000,
    retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=5000),
    deduplication_window_ms=3600000,
)


# Local session for executing tools directly
class LocalExecutionSession:
    _app: "FastMCPTx"

    def __init__(self) -> None:
        pass

    def set_app(self, app: "FastMCPTx") -> None:
        self._app = app

    async def initialize(self, **kwargs: Any) -> Any:
        class MockResult:
            class Capabilities:
                experimental: ClassVar[dict[str, dict[str, str]]] = {"mcp_tx": {"version": "0.1.0"}}

        return MockResult()

    async def send_request(self, request: dict[str, Any]) -> Any:
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not self._app:
            raise RuntimeError("App reference not set")
        tool_def = self._app._registry.get_tool(tool_name)
        if not tool_def:
            raise MCPTxError(f"Tool '{tool_name}' not found.", "TOOL_NOT_FOUND", False)
        logger.info(f"Executing tool '{tool_name}' locally with params: {arguments}")
        return await tool_def["func"](**arguments)


# --- FastMCPTx Application Setup ---
local_session = LocalExecutionSession()
app = FastMCPTx(local_session, config=config, name="MultiAgentResearchApp")
local_session.set_app(app)

# --- State Management ---
# Use a global dictionary for thread-safe access outside Streamlit's main thread
_research_tasks_storage: dict[str, dict[str, Any]] = {}
_tasks_lock = threading.Lock()

# Initialize Streamlit session state if in main thread
try:
    if "research_tasks" not in st.session_state:
        st.session_state.research_tasks = _research_tasks_storage
except Exception:
    # Not in Streamlit context, use global storage directly
    pass


# --- Helper for Web Search ---
def perform_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    """Performs a web search using SerpApi and returns structured results."""
    if not serpapi_key:
        return [{"error": "SerpApi key not configured."}]
    try:
        search = GoogleSearch(
            {
                "q": query,
                "api_key": serpapi_key,
                "num": num_results,
            }
        )
        results = search.get_dict()

        snippets: list[dict[str, Any]] = []
        if "organic_results" in results:
            for res in results["organic_results"]:
                snippets.append(
                    {
                        "title": res.get("title", "N/A"),
                        "link": res.get("link", "#"),
                        "snippet": res.get("snippet", "No snippet available."),
                    }
                )
        return snippets
    except Exception as e:
        logger.error(f"SerpApi search failed: {e}")
        return [{"error": f"Search failed: {e}"}]


# --- Specialized AI Agent Tools (Now with real search) ---
@app.tool(retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=2000))
async def crawl_news(research_id: str, company: str) -> dict[str, Any]:
    """Crawls recent news articles for a given company."""
    logger.info(f"[{research_id}] Starting real news crawl for {company}...")
    query = f"latest news and announcements for {company}"
    search_results = await anyio.to_thread.run_sync(perform_search, query, 5)
    logger.info(f"[{research_id}] Finished news crawl for {company}.")
    return {"company": company, "news_articles": search_results}


@app.tool(retry_policy=RetryPolicy(max_attempts=2, base_delay_ms=10000))
async def analyze_financials(research_id: str, company: str) -> dict[str, Any]:
    """Analyzes quarterly financial reports for a given company."""
    logger.info(f"[{research_id}] Starting real financial analysis for {company}...")
    query = f"{company} quarterly financial report Q2 2025"
    search_results = await anyio.to_thread.run_sync(perform_search, query, 3)
    logger.info(f"[{research_id}] Finished financial analysis for {company}.")
    return {"company": company, "financial_reports": search_results}


@app.tool(retry_policy=RetryPolicy(max_attempts=4, base_delay_ms=3000))
async def scan_social_media(research_id: str, company: str) -> dict[str, Any]:
    """Scans social media for public sentiment about a given company."""
    logger.info(f"[{research_id}] Starting real social media scan for {company}...")
    query = f"social media sentiment analysis for {company} on Twitter and Reddit"
    search_results = await anyio.to_thread.run_sync(perform_search, query, 4)
    logger.info(f"[{research_id}] Finished social media scan for {company}.")
    return {"company": company, "social_media_mentions": search_results}


@app.tool(timeout_ms=120000)  # 2 minute timeout for AI synthesis
async def synthesize_report(research_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    """Synthesizes findings from all agents into a single draft report using OpenAI."""
    logger.info(f"[{research_id}] Synthesizing report with OpenAI from {len(results)} agent results...")
    if not openai_client:
        raise MCPTxError("OpenAI client not initialized.", "CLIENT_ERROR", False)

    # Consolidate search results into a structured prompt
    prompt_content = "Please generate a market trend report based on the following search results:\n\n"
    for result in results:
        company = result.get("company", "Unknown")
        prompt_content += f"--- Data for {company} ---\n"
        for key, value in result.items():
            if key != "company" and isinstance(value, list):
                prompt_content += f"\n**{key.replace('_', ' ').title()}:**\n"
                for item in value:
                    prompt_content += f"- Title: {item.get('title', 'N/A')}\n"
                    prompt_content += f"  Snippet: {item.get('snippet', 'N/A')}\n"
        prompt_content += "\n"

    prompt_content += (
        "\n--- Instructions ---\n"
        "Generate a concise, well-structured markdown report. For each company, provide a summary of the findings "
        "from the news, financial reports, and social media. Conclude with an overall market summary."
    )

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a financial analyst AI."},
                {"role": "user", "content": prompt_content},
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        report_content = response.choices[0].message.content or ""
        logger.info(f"[{research_id}] OpenAI report synthesis complete.")
        return {"draft_report": report_content, "created_at": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise MCPTxError(f"OpenAI API call failed: {e}", "API_ERROR", True)


@app.tool(timeout_ms=3600000)
async def human_approval(research_id: str, draft_report: str) -> dict[str, Any]:
    """Waits for a human to approve the draft report."""
    logger.info(f"[{research_id}] Waiting for human approval...")
    with _tasks_lock:
        _research_tasks_storage[research_id]["status"] = "waiting_for_approval"
        _research_tasks_storage[research_id]["draft_report"] = draft_report
        approval_event = threading.Event()
        _research_tasks_storage[research_id]["approval_event"] = approval_event
    await anyio.to_thread.run_sync(approval_event.wait)
    if _research_tasks_storage[research_id].get("approval_status") == "rejected":
        raise Exception("Report rejected by user.")
    logger.info(f"[{research_id}] Human approval received.")
    return {"approved": True, "approved_at": datetime.utcnow().isoformat()}


@app.tool()
async def finalize_report(research_id: str, final_report: str) -> dict[str, Any]:
    """Simply finalizes the report content for display."""
    logger.info(f"[{research_id}] Finalizing report.")
    await anyio.sleep(1)
    return {"final_report": final_report, "published_at": datetime.utcnow().isoformat()}


# --- Orchestration Logic ---
async def _run_research_flow(research_id: str, companies: list[str]) -> None:
    """The main asynchronous research workflow."""
    try:
        await app.initialize()
        with _tasks_lock:
            _research_tasks_storage[research_id]["status"] = "in_progress"

        # Step 1: Run specialized agents in parallel
        agent_results: list[dict[str, Any]] = []
        try:
            async with anyio.create_task_group() as tg:
                for company in companies:

                    async def run_agent_task(tool_name: str, params: dict[str, Any], idempotency_key: str) -> None:
                        try:
                            result = await app.call_tool(tool_name, params, idempotency_key=idempotency_key)
                            if result.ack:
                                agent_results.append(result.result)
                            else:
                                logger.error(
                                    f"[{research_id}] Tool call failed for {tool_name}: "
                                    f"{result.mcp_tx_meta.error_message}"
                                )
                        except Exception as e:
                            logger.error(f"[{research_id}] Exception in {tool_name}: {e}", exc_info=True)
                            raise

                    tg.start_soon(
                        run_agent_task,
                        "crawl_news",
                        {"research_id": research_id, "company": company},
                        f"{research_id}-crawl-{company}",
                    )
                    tg.start_soon(
                        run_agent_task,
                        "analyze_financials",
                        {"research_id": research_id, "company": company},
                        f"{research_id}-financials-{company}",
                    )
                    tg.start_soon(
                        run_agent_task,
                        "scan_social_media",
                        {"research_id": research_id, "company": company},
                        f"{research_id}-social-{company}",
                    )
        except Exception as e:
            logger.error(f"[{research_id}] One or more agents failed: {e}")
            raise

        with _tasks_lock:
            _research_tasks_storage[research_id]["agent_results"] = agent_results

        # Step 2: Synthesize the report
        synthesis_result = await app.call_tool(
            "synthesize_report",
            {"research_id": research_id, "results": agent_results},
            idempotency_key=f"{research_id}-synthesis",
        )
        draft_report = synthesis_result.result["draft_report"]

        # Step 3: Wait for human approval
        await app.call_tool(
            "human_approval",
            {"research_id": research_id, "draft_report": draft_report},
            idempotency_key=f"{research_id}-approval",
        )

        with _tasks_lock:
            _research_tasks_storage[research_id]["status"] = "publishing"

        # Step 4: Finalize the report
        final_report_content = _research_tasks_storage[research_id].get("final_report_content", draft_report)
        finalization_result = await app.call_tool(
            "finalize_report",
            {"research_id": research_id, "final_report": final_report_content},
            idempotency_key=f"{research_id}-finalize",
        )

        with _tasks_lock:
            _research_tasks_storage[research_id]["status"] = "completed"
            _research_tasks_storage[research_id]["final_report"] = finalization_result.result["final_report"]

    except Exception as e:
        logger.error(f"[{research_id}] Research workflow failed: {e}")
        with _tasks_lock:
            _research_tasks_storage[research_id]["status"] = "failed"
            _research_tasks_storage[research_id]["error"] = str(e)


# --- Public API for Frontend ---
def start_research(research_id: str, companies: list[str]) -> None:
    if research_id in _research_tasks_storage:
        return
    with _tasks_lock:
        _research_tasks_storage[research_id] = {"status": "starting", "companies": companies}
    thread = threading.Thread(target=lambda: anyio.run(_run_research_flow, research_id, companies), daemon=True)
    thread.start()


def get_research_status(research_id: str) -> dict[str, Any]:
    with _tasks_lock:
        return _research_tasks_storage.get(research_id, {"status": "not_found"})


def provide_approval(research_id: str, final_report_content: str, approved: bool) -> dict[str, str]:
    logger.info(f"[{research_id}] 'provide_approval' called. Approved: {approved}")
    with _tasks_lock:
        task = _research_tasks_storage.get(research_id)
        if task and task["status"] == "waiting_for_approval":
            logger.info(f"[{research_id}] Task found and is in 'waiting_for_approval' state.")
            task["approval_status"] = "approved" if approved else "rejected"
            if approved:
                task["status"] = "publishing"
            task["final_report_content"] = final_report_content
            approval_event = task.get("approval_event")
            if approval_event:
                logger.info(f"[{research_id}] Setting approval event.")
                approval_event.set()
            else:
                logger.error(f"[{research_id}] CRITICAL: approval_event not found.")
            return {"status": "approval_received"}
        logger.warning(
            f"[{research_id}] 'provide_approval' failed. State: {task.get('status') if task else 'Not Found'}"
        )
        return {"status": "approval_failed"}


if __name__ == "__main__":
    # This allows running the backend logic directly for testing
    async def run_test() -> None:
        if not openai_client or not serpapi_key:
            print("Please set OPENAI_API_KEY and SERPAPI_KEY in your .env file to run the test.")
            return

        await app.initialize()
        test_research_id = "test-123"

        start_research(test_research_id, ["NVIDIA", "AMD"])

        while get_research_status(test_research_id).get("status") not in ["waiting_for_approval", "failed"]:
            await anyio.sleep(2)
            print(f"Current status: {get_research_status(test_research_id).get('status')}")

        status = get_research_status(test_research_id)
        if status.get("status") == "failed":
            print("--- TEST FAILED ---")
            print(f"Error: {status.get('error')}")
            return

        print("\n--- WAITING FOR APPROVAL ---")
        print(status.get("draft_report"))

        provide_approval(test_research_id, status.get("draft_report", ""), True)

        while get_research_status(test_research_id).get("status") != "completed":
            await anyio.sleep(1)
            print(f"Current status: {get_research_status(test_research_id).get('status')}")

        print("\n--- RESEARCH COMPLETE ---")
        print(get_research_status(test_research_id).get("final_report"))

    anyio.run(run_test)
