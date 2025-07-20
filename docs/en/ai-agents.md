# Building AI Agents with MCP-Tx

This guide demonstrates how to build reliable AI agents using FastMCP-Tx decorators, focusing on multi-step workflows that require robust error handling and delivery guarantees.

## Overview: Smart Research Assistant

We'll build a **Smart Research Assistant** that performs comprehensive research by combining multiple AI tools with MCP-Tx reliability features.

### Agent Capabilities

| Tool | Purpose | MCP-Tx Benefits |
|------|---------|---------------|
| **Web Search** | Find relevant sources | Retry on API failures |
| **Content Analysis** | Summarize and extract insights | Idempotent processing |
| **Fact Checking** | Verify information accuracy | ACK/NACK confirmation |
| **Report Generation** | Create structured output | Transaction tracking |
| **Knowledge Storage** | Persist research results | Duplicate prevention |

### Why MCP-Tx for AI Agents?

AI agents often involve:
- **External API calls** that can fail unexpectedly
- **Long-running workflows** that need recovery
- **Expensive operations** that shouldn't be duplicated
- **Complex state** that requires tracking

MCP-Tx addresses these challenges with automatic retry, idempotency, and delivery guarantees.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Research       │    │   Smart Research │    │   AI Services   │
│  Request        │───▶│   Assistant      │───▶│   (OpenAI, etc) │
└─────────────────┘    │   (FastMCP-Tx)     │    └─────────────────┘
                       └──────────────────┘              │
                                │                        │
                       ┌────────▼────────┐              │
                       │ MCP-Tx Reliability │◀─────────────┘
                       │ • Retry Logic   │
                       │ • Idempotency   │
                       │ • ACK/NACK      │
                       │ • Tracking      │
                       └─────────────────┘
```

## Implementation

### 1. Core Agent Setup

```python
from mcp_tx import FastMCP-Tx, RetryPolicy, MCPTxConfig
import openai
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any

# Configure for AI workloads
config = MCPTxConfig(
    default_timeout_ms=30000,  # AI APIs can be slow
    max_concurrent_requests=5,  # Rate limit consideration
    enable_request_logging=True,
    deduplication_window_ms=600000  # 10 minutes for research tasks
)

# Create research assistant
research_agent = FastMCP-Tx(mcp_session, config=config, name="SmartResearchAssistant")
```

### 2. Web Search Tool

```python
@research_agent.tool(
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
    
    async with aiohttp.ClientSession() as session:
        # Use SerpAPI, Bing, or Google Custom Search
        search_url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "num": num_results,
            "api_key": os.getenv("SERPAPI_KEY")
        }
        
        async with session.get(search_url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Search API error: {response.status}")
            
            data = await response.json()
            
            results = []
            for result in data.get("organic_results", []):
                results.append({
                    "title": result.get("title"),
                    "url": result.get("link"),
                    "snippet": result.get("snippet"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return {
                "query": query,
                "results": results,
                "total_found": len(results)
            }
```

### 3. Content Analysis Tool

```python
@research_agent.tool(
    retry_policy=RetryPolicy(
        max_attempts=5,  # AI APIs can be unreliable
        base_delay_ms=1000
    ),
    idempotency_key_generator=lambda args: f"analyze-{hash(args['content'][:100])}"
)
async def analyze_content(content: str, focus_areas: List[str] = None) -> Dict[str, Any]:
    """Analyze and summarize content using AI with reliability guarantees."""
    
    if not focus_areas:
        focus_areas = ["key_insights", "credibility", "relevance"]
    
    prompt = f"""
    Analyze the following content and provide insights on: {', '.join(focus_areas)}
    
    Content: {content[:2000]}...
    
    Provide a structured analysis with:
    1. Key insights (bullet points)
    2. Credibility assessment (score 1-10)
    3. Relevance to query (score 1-10)
    4. Summary (2-3 sentences)
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "original_length": len(content),
            "analysis": analysis,
            "focus_areas": focus_areas,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # MCP-Tx will retry this automatically
        raise Exception(f"AI analysis failed: {str(e)}")
```

### 4. Fact Checking Tool

```python
@research_agent.tool(
    retry_policy=RetryPolicy(max_attempts=3),
    timeout_ms=20000,
    idempotency_key_generator=lambda args: f"factcheck-{hash(args['claim'])}"
)
async def fact_check(claim: str, sources: List[str] = None) -> Dict[str, Any]:
    """Verify information against reliable sources."""
    
    verification_prompt = f"""
    Fact-check the following claim using the provided sources:
    
    Claim: {claim}
    
    Sources: {json.dumps(sources) if sources else "None provided"}
    
    Provide:
    1. Verification status: VERIFIED, DISPUTED, UNVERIFIED
    2. Confidence score (1-10)
    3. Supporting evidence
    4. Contradicting evidence (if any)
    5. Recommendation for further research
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": verification_prompt}],
            max_tokens=400
        )
        
        verification = response.choices[0].message.content
        
        return {
            "claim": claim,
            "verification": verification,
            "sources_checked": len(sources) if sources else 0,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Fact checking failed: {str(e)}")
```

### 5. Report Generation Tool

```python
@research_agent.tool(
    timeout_ms=25000,
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
    
    report_prompt = f"""
    Create a comprehensive research report based on:
    
    Original Query: {query}
    Research ID: {research_id}
    
    Search Results: {len(search_results)} sources found
    Content Analyses: {len(analyses)} pieces analyzed
    Fact Checks: {len(fact_checks)} claims verified
    
    Generate a structured report with:
    1. Executive Summary
    2. Key Findings
    3. Source Analysis
    4. Credibility Assessment
    5. Recommendations for Action
    6. Areas for Further Research
    
    Format as markdown with clear sections.
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": report_prompt}],
            max_tokens=1000
        )
        
        report_content = response.choices[0].message.content
        
        # Create structured report
        report = {
            "research_id": research_id,
            "query": query,
            "generated_at": datetime.utcnow().isoformat(),
            "content": report_content,
            "metadata": {
                "sources_count": len(search_results),
                "analyses_count": len(analyses),
                "fact_checks_count": len(fact_checks)
            },
            "status": "completed"
        }
        
        return report
        
    except Exception as e:
        raise Exception(f"Report generation failed: {str(e)}")
```

### 6. Knowledge Storage Tool

```python
@research_agent.tool(
    idempotency_key_generator=lambda args: f"save-{args['research_id']}"
)
async def save_research(research_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """Save research results for future reference."""
    
    # In production, this would save to a database
    filename = f"research_{research_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = f"./research_results/{filename}"
    
    os.makedirs("./research_results", exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
    
    return {
        "research_id": research_id,
        "saved_to": filepath,
        "saved_at": datetime.utcnow().isoformat(),
        "file_size": os.path.getsize(filepath)
    }
```

## Orchestrating the Research Workflow

### Multi-Step Research Process

```python
class SmartResearchAssistant:
    """Orchestrates the complete research workflow with MCP-Tx reliability."""
    
    def __init__(self, agent: FastMCP-Tx):
        self.agent = agent
        self.research_sessions = {}
    
    async def conduct_research(self, query: str, research_id: str = None) -> Dict[str, Any]:
        """Conduct comprehensive research with full MCP-Tx tracking."""
        
        if not research_id:
            research_id = f"research_{int(datetime.utcnow().timestamp())}"
        
        self.research_sessions[research_id] = {
            "query": query,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "steps": []
        }
        
        try:
            # Step 1: Web Search
            print(f"🔍 Searching for: {query}")
            search_result = await self.agent.call_tool(
                "web_search",
                {"query": query, "num_results": 8},
                idempotency_key=f"search-{research_id}"
            )
            
            self._record_step(research_id, "search", search_result)
            search_data = search_result.result
            
            # Step 2: Analyze each source
            print(f"📊 Analyzing {len(search_data['results'])} sources")
            analyses = []
            
            for i, source in enumerate(search_data['results']):
                try:
                    analysis_result = await self.agent.call_tool(
                        "analyze_content",
                        {
                            "content": f"{source['title']} {source['snippet']}",
                            "focus_areas": ["relevance", "credibility", "key_insights"]
                        },
                        idempotency_key=f"analyze-{research_id}-{i}"
                    )
                    analyses.append(analysis_result.result)
                    self._record_step(research_id, f"analysis_{i}", analysis_result)
                    
                except Exception as e:
                    print(f"⚠️ Analysis failed for source {i}: {e}")
                    continue
            
            # Step 3: Fact check key claims
            print(f"✅ Fact checking key claims")
            fact_checks = []
            
            # Extract claims from analyses for fact checking
            for i, analysis in enumerate(analyses[:3]):  # Check top 3 analyses
                try:
                    fact_check_result = await self.agent.call_tool(
                        "fact_check",
                        {
                            "claim": analysis["analysis"][:200],  # First part of analysis
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
            print(f"📄 Generating research report")
            report_result = await self.agent.call_tool(
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
            print(f"💾 Saving research results")
            save_result = await self.agent.call_tool(
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
            
            return {
                "research_id": research_id,
                "status": "success",
                "report": report,
                "metadata": {
                    "sources_found": len(search_data['results']),
                    "analyses_completed": len(analyses),
                    "fact_checks_performed": len(fact_checks),
                    "total_rmcp_attempts": sum(
                        step["attempts"] for step in self.research_sessions[research_id]["steps"]
                    )
                }
            }
            
        except Exception as e:
            self.research_sessions[research_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
            raise
    
    def _record_step(self, research_id: str, step_name: str, result):
        """Record each step with MCP-Tx metadata."""
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
```

## Usage Example

```python
async def main():
    """Example usage of the Smart Research Assistant."""
    
    # Initialize the research assistant
    async with research_agent:
        assistant = SmartResearchAssistant(research_agent)
        
        # Conduct research
        research_query = "Impact of AI on software development productivity in 2024"
        
        try:
            result = await assistant.conduct_research(research_query)
            
            print(f"✨ Research completed successfully!")
            print(f"📊 Sources analyzed: {result['metadata']['sources_found']}")
            print(f"🔄 Total MCP-Tx retry attempts: {result['metadata']['total_rmcp_attempts']}")
            print(f"📄 Report generated and saved")
            
            # Display the research report
            print("\\n" + "="*50)
            print("RESEARCH REPORT")
            print("="*50)
            print(result['report']['content'])
            
        except Exception as e:
            print(f"❌ Research failed: {e}")

# Run the research assistant
if __name__ == "__main__":
    asyncio.run(main())
```

## Key Benefits of MCP-Tx for AI Agents

### 1. **Reliability in AI Workflows**

```python
# Without MCP-Tx: Manual error handling
try:
    result = await openai_api_call()
except Exception:
    # Manual retry logic, no guarantees
    pass

# With MCP-Tx: Automatic reliability
@agent.tool(retry_policy=RetryPolicy(max_attempts=3))
async def ai_analysis(content: str) -> dict:
    # Automatic retry with exponential backoff
    return await openai_api_call(content)
```

### 2. **Cost Control with Idempotency**

```python
# Prevents expensive AI API calls from being duplicated
@agent.tool(idempotency_key_generator=lambda args: f"analysis-{hash(args['content'])}")
async def expensive_ai_analysis(content: str) -> dict:
    # This won't be called again for the same content
    return await costly_ai_service(content)
```

### 3. **Workflow Transparency**

```python
# Track every step of complex AI workflows
for step in research_session["steps"]:
    print(f"Step {step['step']}: {step['attempts']} attempts, ACK: {step['ack']}")
```

## Best Practices

### 1. **Design for Idempotency**
- Use content hashes for idempotency keys
- Make AI operations deterministic where possible
- Cache expensive computations

### 2. **Handle AI API Failures Gracefully**
- Set appropriate retry policies for different AI services
- Use timeouts that account for AI processing time
- Implement fallback strategies

### 3. **Monitor and Optimize**
- Track retry attempts and failure rates
- Monitor API costs and usage patterns
- Optimize retry policies based on real performance

### 4. **Structure for Observability**
- Log each workflow step with MCP-Tx metadata
- Preserve intermediate results for debugging
- Implement comprehensive error reporting

## Extending the Agent

The Smart Research Assistant can be extended with additional tools:

- **Document Analysis** - PDF/document processing
- **Image Analysis** - Visual content understanding
- **Data Visualization** - Chart and graph generation
- **Multi-language Support** - Translation and localization
- **Real-time Updates** - Continuous research monitoring

Each new tool benefits from MCP-Tx's reliability features, making the entire agent more robust and production-ready.

## See Also

- [Advanced Examples](examples/advanced.md) - Complex workflow patterns
- [Configuration Guide](configuration.md) - Optimizing for AI workloads
- [Performance Guide](performance.md) - Scaling AI agent deployments

---

**Previous**: [Integration Guide](examples/integration.md) | **Next**: [Configuration Guide](configuration.md)