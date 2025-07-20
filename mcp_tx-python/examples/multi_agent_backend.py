"""
Multi-Agent Research Backend using MCP-Tx

This backend orchestrates multiple autonomous AI agents to perform a comprehensive
research task, demonstrating the power of MCP-Tx for long-running, multi-step,
and collaborative AI workflows.
"""

import asyncio
import logging
import random
import threading
from datetime import datetime
from typing import Any, ClassVar

import anyio
from mcp_tx import FastMCPTx, MCPTxConfig, RetryPolicy

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# MCP-Tx Configuration for long-running, expensive AI tasks
config = MCPTxConfig(
    default_timeout_ms=300000,  # 5 minutes for each step
    retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=5000),  # Retry up to 3 times with 5s base delay
    deduplication_window_ms=3600000,  # 1 hour deduplication window
)


# A mock MCP session is used here for demonstration purposes.
# In a real application, this would connect to your MCP server.
class MockMCPSession:
    async def initialize(self, **kwargs):
        class MockResult:
            class Capabilities:
                experimental: ClassVar[dict[str, dict[str, str]]] = {"mcp_tx": {"version": "0.1.0"}}

        return MockResult()

    async def send_request(self, request: dict) -> dict:
        return {"result": {"status": "ok"}}


# --- FastMCPTx Application Setup ---
app = FastMCPTx(MockMCPSession(), config=config, name="MultiAgentResearchApp")

# --- State Management (in-memory for this example) ---
research_tasks: dict[str, dict[str, Any]] = {}


# --- Specialized AI Agent Tools ---
@app.tool(retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=2000))
async def crawl_news(research_id: str, company: str) -> dict[str, Any]:
    """Crawls recent news articles for a given company."""
    logger.info(f"[{research_id}] Starting news crawl for {company}...")
    await anyio.sleep(random.uniform(5, 10))  # Simulate long-running task
    logger.info(f"[{research_id}] Finished news crawl for {company}.")
    return {
        "company": company,
        "articles": [
            {"title": f"{company} announces record profits", "source": "News Site A"},
            {"title": f"New product launch from {company}", "source": "Tech Blog B"},
        ],
    }


@app.tool(retry_policy=RetryPolicy(max_attempts=2, base_delay_ms=10000))
async def analyze_financials(research_id: str, company: str) -> dict[str, Any]:
    """Analyzes quarterly financial reports for a given company."""
    logger.info(f"[{research_id}] Starting financial analysis for {company}...")
    await anyio.sleep(random.uniform(8, 15))  # Simulate long-running, expensive task
    logger.info(f"[{research_id}] Finished financial analysis for {company}.")
    return {
        "company": company,
        "summary": "Strong revenue growth, but margins are shrinking.",
        "quarter": "Q2 2025",
    }


@app.tool(retry_policy=RetryPolicy(max_attempts=4, base_delay_ms=3000))
async def scan_social_media(research_id: str, company: str) -> dict[str, Any]:
    """Scans social media for public sentiment about a given company."""
    logger.info(f"[{research_id}] Starting social media scan for {company}...")
    await anyio.sleep(random.uniform(6, 12))  # Simulate long-running task
    logger.info(f"[{research_id}] Finished social media scan for {company}.")
    return {
        "company": company,
        "sentiment": "Positive",
        "trending_topics": ["#NewProduct", "#Innovation"],
    }


@app.tool()
async def synthesize_report(research_id: str, results: list[dict]) -> dict[str, Any]:
    """Synthesizes findings from all agents into a single draft report."""
    logger.info(f"[{research_id}] Synthesizing report from {len(results)} agent results...")
    await anyio.sleep(5)

    report_content = f"## Market Trend Report: {datetime.now().strftime('%Y-%m-%d')}\n\n"
    for result in results:
        company = result.get("company", "Unknown")
        report_content += f"### Analysis for {company}\n"
        if "articles" in result:
            report_content += f"- **News:** Found {len(result['articles'])} relevant articles.\n"
        if "summary" in result:
            report_content += f"- **Financials:** {result['summary']}\n"
        if "sentiment" in result:
            report_content += f"- **Social Media Sentiment:** {result['sentiment']}\n\n"

    logger.info(f"[{research_id}] Report synthesis complete.")
    return {"draft_report": report_content, "created_at": datetime.utcnow().isoformat()}


@app.tool(timeout_ms=3600000)  # 1 hour timeout for human approval
async def human_approval(research_id: str, draft_report: str) -> dict[str, Any]:
    """Waits for a human to approve the draft report. This is the 'Human as a Server' part."""
    logger.info(f"[{research_id}] Waiting for human approval...")
    research_tasks[research_id]["status"] = "waiting_for_approval"
    research_tasks[research_id]["draft_report"] = draft_report
    approval_event = anyio.Event()
    research_tasks[research_id]["approval_event"] = approval_event
    await approval_event.wait()

    if research_tasks[research_id].get("approval_status") == "rejected":
        raise Exception("Report rejected by user.")

    logger.info(f"[{research_id}] Human approval received.")
    return {"approved": True, "approved_at": datetime.utcnow().isoformat()}


@app.tool()
async def publish_to_internal_wiki(research_id: str, final_report: str) -> dict[str, Any]:
    """Publishes the final report to a wiki."""
    logger.info(f"[{research_id}] Publishing final report...")
    await anyio.sleep(2)
    wiki_url = f"https://internal.wiki/{research_id}"
    logger.info(f"[{research_id}] Report published to {wiki_url}")
    return {"url": wiki_url, "published_at": datetime.utcnow().isoformat()}


# --- Orchestration Logic ---


async def _run_research_flow(research_id: str, companies: list[str]):
    """The main asynchronous research workflow."""
    try:
        research_tasks[research_id]["status"] = "in_progress"

        # Step 1: Run specialized agents in parallel
        agent_results = []
        try:
            async with anyio.create_task_group() as tg:
                for company in companies:

                    async def run_agent_task(tool_name, params, idempotency_key):
                        result = await app.call_tool(tool_name, params, idempotency_key=idempotency_key)
                        if result.ack:
                            agent_results.append(result.result)

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

        research_tasks[research_id]["agent_results"] = agent_results

        # Step 2: Synthesize the report
        synthesis_result = await app.call_tool(
            "synthesize_report",
            {"research_id": research_id, "results": research_tasks[research_id]["agent_results"]},
            idempotency_key=f"{research_id}-synthesis",
        )
        draft_report = synthesis_result.result["draft_report"]

        # Step 3: Wait for human approval
        await app.call_tool(
            "human_approval",
            {"research_id": research_id, "draft_report": draft_report},
            idempotency_key=f"{research_id}-approval",
        )

        # Step 4: Publish the final report
        final_report_content = research_tasks[research_id].get("final_report_content", draft_report)
        publish_result = await app.call_tool(
            "publish_to_internal_wiki",
            {"research_id": research_id, "final_report": final_report_content},
            idempotency_key=f"{research_id}-publish",
        )

        research_tasks[research_id]["status"] = "completed"
        research_tasks[research_id]["final_url"] = publish_result.result["url"]

    except Exception as e:
        logger.error(f"[{research_id}] Research workflow failed: {e}")
        research_tasks[research_id]["status"] = "failed"
        research_tasks[research_id]["error"] = str(e)


# --- Public API for Frontend ---


def start_research(research_id: str, companies: list[str]):
    """Starts the research workflow in a background thread."""
    if research_id in research_tasks:
        return  # Avoid starting the same research twice

    research_tasks[research_id] = {"status": "starting", "companies": companies}

    def run_background():
        anyio.run(_run_research_flow, research_id, companies)

    thread = threading.Thread(target=run_background, daemon=True)
    thread.start()


def get_research_status(research_id: str) -> dict[str, Any]:
    """Gets the status of a research task."""
    return research_tasks.get(research_id, {"status": "not_found"})


def provide_approval(research_id: str, final_report_content: str, approved: bool):
    """Provides human approval to a waiting research task."""
    if research_id in research_tasks and research_tasks[research_id]["status"] == "waiting_for_approval":
        if approved:
            research_tasks[research_id]["approval_status"] = "approved"
        else:
            research_tasks[research_id]["approval_status"] = "rejected"
        research_tasks[research_id]["final_report_content"] = final_report_content
        research_tasks[research_id]["approval_event"].set()
        return {"status": "approval_received"}
    return {"status": "approval_failed"}


if __name__ == "__main__":
    # This allows running the backend logic directly for testing
    async def run_test():
        await app.initialize()
        test_research_id = "test-123"

        thread = threading.Thread(target=start_research, args=(test_research_id, ["Apple", "Google"]), daemon=True)
        thread.start()

        # Wait until it needs approval
        while get_research_status(test_research_id).get("status") != "waiting_for_approval":
            await anyio.sleep(1)
            print(f"Current status: {get_research_status(test_research_id).get('status')}")

        print("--- WAITING FOR APPROVAL ---")
        print(get_research_status(test_research_id).get("draft_report"))

        # Simulate approval
        provide_approval(test_research_id, "This is the final, human-edited report.", True)

        # Wait for completion
        while get_research_status(test_research_id).get("status") != "completed":
            await anyio.sleep(1)
            print(f"Current status: {get_research_status(test_research_id).get('status')}")

        print("--- RESEARCH COMPLETE ---")
        print(get_research_status(test_research_id))

    anyio.run(run_test)
