#!/usr/bin/env python3
"""
Smart Research Assistant - AI Agent Example using FastRMCP

This example demonstrates how to build a reliable AI agent that performs
comprehensive research using multiple AI tools with RMCP reliability features.

Features:
- Web search with automatic retry
- AI-powered content analysis 
- Fact checking with source verification
- Structured report generation
- Persistent knowledge storage

Usage:
    python smart_research_assistant.py "AI impact on software development 2024"
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import AsyncMock

# Import RMCP
from rmcp import FastRMCP, RetryPolicy, RMCPConfig


class MockAIService:
    """Mock AI service for demonstration purposes."""
    
    @staticmethod
    async def search_web(query: str, num_results: int = 5) -> Dict[str, Any]:
        """Mock web search API."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Mock search results
        results = [
            {
                "title": f"AI Development Trends {2024 - i}",
                "url": f"https://example{i}.com/ai-development-{2024-i}",
                "snippet": f"Research shows AI is transforming software development through automated code generation, testing, and deployment processes. Impact factor: {90 + i}%"
            }
            for i in range(min(num_results, 5))
        ]
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
    
    @staticmethod
    async def analyze_content(content: str) -> str:
        """Mock AI content analysis."""
        await asyncio.sleep(0.2)  # Simulate AI processing time
        
        # Sometimes fail to demonstrate retry functionality
        import random
        if random.random() < 0.1:  # 10% failure rate
            raise Exception("AI service temporarily unavailable")
        
        return f"""
        ## Content Analysis Results

        **Key Insights:**
        - AI tools are significantly improving developer productivity
        - Automated code generation is becoming mainstream
        - Code quality and testing are being enhanced by AI

        **Credibility Score:** 8/10
        **Relevance Score:** 9/10

        **Summary:** The content discusses the transformative impact of AI on software development, 
        highlighting improvements in productivity, code quality, and automation capabilities.
        """
    
    @staticmethod
    async def fact_check(claim: str, sources: List[str]) -> str:
        """Mock fact checking service."""
        await asyncio.sleep(0.15)  # Simulate processing time
        
        return f"""
        ## Fact Check Results

        **Claim:** {claim[:100]}...

        **Verification Status:** VERIFIED
        **Confidence Score:** 8/10

        **Supporting Evidence:**
        - Multiple industry reports confirm AI productivity gains
        - Developer surveys show widespread AI tool adoption
        - Measurable improvements in code quality metrics

        **Recommendation:** Information appears accurate based on available sources.
        """
    
    @staticmethod
    async def generate_report(data: Dict[str, Any]) -> str:
        """Mock report generation service."""
        await asyncio.sleep(0.3)  # Simulate report generation time
        
        query = data.get("query", "Unknown")
        sources_count = data.get("sources_count", 0)
        analyses_count = data.get("analyses_count", 0)
        
        return f"""
# Research Report: {query}

## Executive Summary

This research investigated {query.lower()}, analyzing {sources_count} sources 
and conducting {analyses_count} detailed content analyses. The findings indicate 
significant positive impacts of AI on software development productivity.

## Key Findings

1. **Productivity Gains**: AI tools are delivering 20-40% productivity improvements
2. **Code Quality**: Automated testing and review tools are reducing bugs by 25-30%
3. **Developer Experience**: AI assistance is improving developer satisfaction and reducing cognitive load
4. **Adoption Trends**: Enterprise adoption of AI development tools is accelerating

## Source Analysis

- **Total Sources Analyzed:** {sources_count}
- **Average Credibility Score:** 8.2/10
- **Information Currency:** Recent (2024) data available

## Recommendations

1. **Immediate Actions:**
   - Evaluate AI-powered development tools for your team
   - Establish best practices for AI-assisted coding
   - Measure productivity impact with clear metrics

2. **Strategic Considerations:**
   - Invest in developer training for AI tools
   - Update development processes to incorporate AI assistance
   - Monitor emerging AI development technologies

## Areas for Further Research

- Long-term impact on software architecture patterns
- Skills evolution requirements for developers
- Integration challenges in legacy systems

---
*Report generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC*
        """


class SmartResearchAssistant:
    """
    AI-powered research assistant using FastRMCP for reliability.
    
    This class orchestrates a complete research workflow:
    1. Web search for relevant sources
    2. AI-powered content analysis
    3. Fact checking of key claims
    4. Structured report generation
    5. Results storage with deduplication
    """
    
    def __init__(self, rmcp_app: FastRMCP):
        self.app = rmcp_app
        self.research_sessions = {}
        self.ai_service = MockAIService()
    
    async def setup_tools(self):
        """Register all research tools with RMCP reliability."""
        
        @self.app.tool(
            retry_policy=RetryPolicy(
                max_attempts=3,
                base_delay_ms=2000,
                backoff_multiplier=2.0
            ),
            timeout_ms=15000,
            idempotency_key_generator=lambda args: f"search-{hash(args['query'])}"
        )
        async def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
            """Search the web for information with automatic retry on failures."""
            print(f"🔍 Searching for: {query}")
            
            try:
                result = await self.ai_service.search_web(query, num_results)
                print(f"   Found {result['total_found']} results")
                return result
            except Exception as e:
                print(f"   Search failed: {e}")
                raise
        
        @self.app.tool(
            retry_policy=RetryPolicy(
                max_attempts=5,  # AI APIs can be unreliable
                base_delay_ms=1000
            ),
            idempotency_key_generator=lambda args: f"analyze-{hash(args['content'][:100])}"
        )
        async def analyze_content(content: str) -> Dict[str, Any]:
            """Analyze content using AI with reliability guarantees."""
            print(f"📊 Analyzing content ({len(content)} chars)")
            
            try:
                analysis = await self.ai_service.analyze_content(content)
                print(f"   Analysis completed")
                return {
                    "original_length": len(content),
                    "analysis": analysis,
                    "processed_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                print(f"   Analysis failed: {e}")
                raise
        
        @self.app.tool(
            retry_policy=RetryPolicy(max_attempts=3),
            timeout_ms=20000,
            idempotency_key_generator=lambda args: f"factcheck-{hash(args['claim'])}"
        )
        async def fact_check(claim: str, sources: List[str] = None) -> Dict[str, Any]:
            """Verify information against reliable sources."""
            print(f"✅ Fact checking claim ({len(claim)} chars)")
            
            try:
                verification = await self.ai_service.fact_check(claim, sources or [])
                print(f"   Fact check completed")
                return {
                    "claim": claim,
                    "verification": verification,
                    "sources_checked": len(sources) if sources else 0,
                    "checked_at": datetime.utcnow().isoformat()
                }
            except Exception as e:
                print(f"   Fact check failed: {e}")
                raise
        
        @self.app.tool(
            timeout_ms=30000,
            idempotency_key_generator=lambda args: f"report-{args['research_id']}"
        )
        async def generate_research_report(
            research_id: str,
            search_results: List[Dict],
            analyses: List[Dict],
            fact_checks: List[Dict],
            query: str
        ) -> Dict[str, Any]:
            """Generate a comprehensive research report."""
            print(f"📄 Generating research report")
            
            try:
                report_data = {
                    "query": query,
                    "sources_count": len(search_results),
                    "analyses_count": len(analyses),
                    "fact_checks_count": len(fact_checks)
                }
                
                report_content = await self.ai_service.generate_report(report_data)
                
                report = {
                    "research_id": research_id,
                    "query": query,
                    "generated_at": datetime.utcnow().isoformat(),
                    "content": report_content,
                    "metadata": report_data,
                    "status": "completed"
                }
                
                print(f"   Report generated successfully")
                return report
                
            except Exception as e:
                print(f"   Report generation failed: {e}")
                raise
        
        @self.app.tool(
            idempotency_key_generator=lambda args: f"save-{args['research_id']}"
        )
        async def save_research(research_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
            """Save research results for future reference."""
            print(f"💾 Saving research results")
            
            # Create results directory
            results_dir = "./research_results"
            os.makedirs(results_dir, exist_ok=True)
            
            # Save report
            filename = f"research_{research_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(results_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            result = {
                "research_id": research_id,
                "saved_to": filepath,
                "saved_at": datetime.utcnow().isoformat(),
                "file_size": os.path.getsize(filepath)
            }
            
            print(f"   Saved to {filepath} ({result['file_size']} bytes)")
            return result
    
    async def conduct_research(self, query: str, research_id: str = None) -> Dict[str, Any]:
        """
        Conduct comprehensive research with full RMCP tracking.
        
        Args:
            query: Research query
            research_id: Optional research session ID
            
        Returns:
            Complete research results with metadata
        """
        if not research_id:
            research_id = f"research_{int(datetime.utcnow().timestamp())}"
        
        print(f"\\n🚀 Starting research session: {research_id}")
        print(f"📝 Query: {query}")
        
        # Initialize research session
        self.research_sessions[research_id] = {
            "query": query,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "steps": []
        }
        
        try:
            # Step 1: Web Search
            print(f"\\n--- Step 1: Web Search ---")
            search_result = await self.app.call_tool(
                "web_search",
                {"query": query, "num_results": 6},
                idempotency_key=f"search-{research_id}"
            )
            
            self._record_step(research_id, "search", search_result)
            search_data = search_result.result
            
            # Step 2: Analyze each source
            print(f"\\n--- Step 2: Content Analysis ---")
            analyses = []
            
            for i, source in enumerate(search_data['results'][:3]):  # Analyze top 3 sources
                try:
                    analysis_result = await self.app.call_tool(
                        "analyze_content",
                        {
                            "content": f"Title: {source['title']}\\n\\nContent: {source['snippet']}"
                        },
                        idempotency_key=f"analyze-{research_id}-{i}"
                    )
                    analyses.append(analysis_result.result)
                    self._record_step(research_id, f"analysis_{i}", analysis_result)
                    
                except Exception as e:
                    print(f"⚠️ Analysis failed for source {i}: {e}")
                    continue
            
            # Step 3: Fact check key claims
            print(f"\\n--- Step 3: Fact Checking ---")
            fact_checks = []
            
            for i, analysis in enumerate(analyses[:2]):  # Check top 2 analyses
                try:
                    # Extract first claim from analysis for fact checking
                    claim = analysis["analysis"][:300]  # First 300 chars
                    
                    fact_check_result = await self.app.call_tool(
                        "fact_check",
                        {
                            "claim": claim,
                            "sources": [s["url"] for s in search_data['results'][:3]]
                        },
                        idempotency_key=f"factcheck-{research_id}-{i}"
                    )
                    fact_checks.append(fact_check_result.result)
                    self._record_step(research_id, f"factcheck_{i}", fact_check_result)
                    
                except Exception as e:
                    print(f"⚠️ Fact check failed for claim {i}: {e}")
                    continue
            
            # Step 4: Generate comprehensive report
            print(f"\\n--- Step 4: Report Generation ---")
            report_result = await self.app.call_tool(
                "generate_research_report",
                {
                    "research_id": research_id,
                    "search_results": search_data['results'],
                    "analyses": analyses,
                    "fact_checks": fact_checks,
                    "query": query
                },
                idempotency_key=f"report-{research_id}"
            )
            
            self._record_step(research_id, "report", report_result)
            report = report_result.result
            
            # Step 5: Save results
            print(f"\\n--- Step 5: Save Results ---")
            save_result = await self.app.call_tool(
                "save_research",
                {
                    "research_id": research_id,
                    "report": report
                },
                idempotency_key=f"save-{research_id}"
            )
            
            self._record_step(research_id, "save", save_result)
            
            # Update session status
            self.research_sessions[research_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "total_steps": len(self.research_sessions[research_id]["steps"]),
                "final_report": report
            })
            
            # Calculate RMCP statistics
            total_attempts = sum(step["attempts"] for step in self.research_sessions[research_id]["steps"])
            successful_steps = sum(1 for step in self.research_sessions[research_id]["steps"] if step["ack"])
            
            result = {
                "research_id": research_id,
                "status": "success",
                "report": report,
                "metadata": {
                    "sources_found": len(search_data['results']),
                    "analyses_completed": len(analyses),
                    "fact_checks_performed": len(fact_checks),
                    "total_rmcp_attempts": total_attempts,
                    "successful_steps": successful_steps,
                    "file_saved": save_result.result["saved_to"]
                }
            }
            
            print(f"\\n✨ Research completed successfully!")
            print(f"📊 Sources found: {result['metadata']['sources_found']}")
            print(f"📈 Analyses completed: {result['metadata']['analyses_completed']}")
            print(f"✅ Fact checks performed: {result['metadata']['fact_checks_performed']}")
            print(f"🔄 Total RMCP attempts: {result['metadata']['total_rmcp_attempts']}")
            print(f"✅ Successful steps: {result['metadata']['successful_steps']}")
            print(f"💾 Report saved to: {result['metadata']['file_saved']}")
            
            return result
            
        except Exception as e:
            print(f"\\n❌ Research failed: {e}")
            self.research_sessions[research_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
            raise
    
    def _record_step(self, research_id: str, step_name: str, result):
        """Record each step with RMCP metadata."""
        self.research_sessions[research_id]["steps"].append({
            "step": step_name,
            "request_id": result.rmcp_meta.request_id,
            "attempts": result.rmcp_meta.attempts,
            "duplicate": result.rmcp_meta.duplicate,
            "ack": result.rmcp_meta.ack,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_research_status(self, research_id: str) -> Dict[str, Any]:
        """Get detailed status of a research session."""
        return self.research_sessions.get(research_id, {"error": "Research ID not found"})
    
    def list_research_sessions(self) -> List[Dict[str, Any]]:
        """List all research sessions."""
        return [
            {
                "research_id": rid,
                "query": session["query"],
                "status": session["status"],
                "started_at": session["started_at"]
            }
            for rid, session in self.research_sessions.items()
        ]


async def main():
    """Main function to run the Smart Research Assistant."""
    
    # Get research query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "AI impact on software development productivity in 2024"
    
    print("🤖 Smart Research Assistant with RMCP")
    print("=" * 50)
    
    # Create mock MCP session for demonstration
    mock_mcp_session = AsyncMock()
    
    # Configure RMCP for AI workloads
    config = RMCPConfig(
        default_timeout_ms=30000,  # AI APIs can be slow
        max_concurrent_requests=5,  # Rate limiting consideration
        enable_request_logging=True,
        deduplication_window_ms=600000  # 10 minutes for research tasks
    )
    
    # Create FastRMCP app
    research_app = FastRMCP(
        mock_mcp_session,
        config=config,
        name="SmartResearchAssistant"
    )
    
    try:
        # Initialize and run research
        async with research_app:
            assistant = SmartResearchAssistant(research_app)
            await assistant.setup_tools()
            
            # Conduct research
            result = await assistant.conduct_research(query)
            
            # Display results
            print("\\n" + "=" * 60)
            print("📄 RESEARCH REPORT")
            print("=" * 60)
            print(result['report']['content'])
            
            print("\\n" + "=" * 60)
            print("📊 RMCP RELIABILITY METRICS")
            print("=" * 60)
            
            # Show RMCP statistics for each step
            for step in assistant.research_sessions[result['research_id']]["steps"]:
                print(f"• {step['step']}: {step['attempts']} attempts, "
                      f"ACK: {'✅' if step['ack'] else '❌'}, "
                      f"Duplicate: {'🔄' if step['duplicate'] else '🆕'}")
            
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))