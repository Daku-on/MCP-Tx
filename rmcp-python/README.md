# MCP-Tx Python SDK

[![Tests](https://github.com/Daku-on/MCP-Tx/actions/workflows/test.yml/badge.svg)](https://github.com/Daku-on/MCP-Tx/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

> **MCP-Tx: Production-ready Python SDK for Reliable Model Context Protocol (MCP-Tx)**  
> Transforms any MCP session into a **reliable ecosystem** where AI agents, tools, and **human operators** can collaboratively execute complex workflows with delivery guarantees, automatic retry, and request deduplication.

🌟 **Revolutionary Concept**: MCP-Tx treats **humans as servers** in the workflow, allowing seamless integration of human approval, judgment, and interaction within automated AI agent processes—all with the same reliability guarantees.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Daku-on/MCP-Tx.git
cd MCP-Tx/mcp-tx-python

# Install dependencies
uv install

# Run tests
uv run pytest tests/ -v
```

### Basic Usage

```python
from mcp_tx import FastMCPTx, RetryPolicy
from mcp.client.session import ClientSession

# Wrap your existing MCP session
app = FastMCPTx(mcp_session)

@app.tool()
async def reliable_file_writer(path: str, content: str) -> dict:
    """Write file with automatic retry and idempotency."""
    with open(path, 'w') as f:
        f.write(content)
    return {"path": path, "size": len(content)}

# Use with automatic MCP-Tx reliability
async with app:
    result = await app.call_tool("reliable_file_writer", {
        "path": "/tmp/data.json", 
        "content": json.dumps(data)
    })
    
    print(f"ACK: {result.mcp_tx_meta.ack}")           # True - confirmed receipt
    print(f"Processed: {result.mcp_tx_meta.processed}") # True - actually executed  
    print(f"Attempts: {result.mcp_tx_meta.attempts}")    # How many retries needed
```

## Key Features

✅ **Decorator-based API** - Simple `@app.tool()` decorator for any function  
✅ **Automatic retry** - Configurable retry policies with exponential backoff  
✅ **Request deduplication** - Prevents duplicate tool executions  
✅ **ACK/NACK guarantees** - Know when tools actually executed  
✅ **Thread-safe** - Concurrent tool calls with proper async patterns  
✅ **Type-safe** - Comprehensive type hints throughout  
✅ **Cross-platform** - Works with both asyncio and trio  
✅ **100% MCP compatible** - Transparent fallback to standard MCP  

## Documentation

📖 **[Complete Documentation](../docs/en/README.md)** - Comprehensive guides and API reference  
🇯🇵 **[日本語ドキュメント](../docs/jp/README_jp.md)** - 完全な日本語ドキュメント

### Quick Links

- [**Getting Started**](../docs/en/getting-started.md) - 5-minute setup guide
- [**Architecture Overview**](../docs/en/architecture.md) - How MCP-Tx enhances MCP
- [**API Reference**](../docs/en/api/mcp-tx-session.md) - Detailed API documentation
- [**Examples**](../docs/en/examples/basic.md) - Common usage patterns
- [**Advanced Examples**](../docs/en/examples/advanced.md) - Complex workflows and integrations

## Core Concept: Humans as Servers

**MCP-Tx's revolutionary insight**: In complex AI workflows, **humans are servers too**. Whether it's an automated tool processing data or a human providing approval, they're both "servers" that receive requests and return responses.

```
┌──────────────────────┐
│  MCP-Tx Orchestrator   │
│   (Client/Agent)     │
└──────────────────────┘
           │
           │ call_tool()
           ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                     MCP-Tx Unified Interface                      │
│    Same API for both automated tools and human interactions     │
└────────────────────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
    ┌─────────────────┐                ┌─────────────────┐
    │ 🤖 AI/Tool Server │                │ 👤 Human Server   │
    │                 │                │ (via UI/Approval) │
    │ • Database ops    │                │                 │
    │ • API calls       │                │ • Approval       │
    │ • File processing │                │ • Decision making │
    │ • Calculations    │                │ • Content review  │
    └─────────────────┘                └─────────────────┘

  ✅ Same reliability guarantees for both: retry, idempotency, ACK/NACK, tracing
```

### Example: Human-in-the-Loop Email Workflow

```python
# All requests use the same call_tool() interface
print("Step 1: AI generates email draft...")
await app.call_tool("generate_email", {"topic": "project_update"})

print("Step 2: Human approval (UI shows draft, waits for click)...")
approval = await app.call_tool("human_approval", {
    "message": "Review and approve this email?",
    "timeout_ms": 3600000  # 1 hour
})

if approval.mcp_tx_meta.ack:  # Human clicked "Approve"
    print("Step 3: Send email...")
    await app.call_tool("send_email", {})
```

**The power**: Human approval gets the same reliability features as automated tools:
- ⚙️ **Idempotency**: Double-clicking "Approve" won't send duplicate emails
- 🔄 **Retry**: Network failures are automatically handled
- 📋 **Tracing**: Complete audit trail of who approved what, when
- ⏱️ **Timeouts**: Configurable timeout for human responses

## Why Server Developers Should Adopt MCP-Tx

### 💰 Cost Reduction & Resource Protection

| Benefit | How MCP-Tx Helps | Impact |
|---------|------------------|--------|
| **Prevents expensive re-computation** | Idempotency keys cache results of LLM calls, DB queries | 60-80% reduction in duplicate API costs |
| **Reduces server load** | Smart client retry with exponential backoff prevents thundering herd | Smoother traffic, better performance |
| **Simplifies server code** | Server just marks errors as "retryable", client handles complexity | Less error-handling code to maintain |

### 🔍 Enhanced Observability & Debugging

```python
# Server logs with RMCP transaction IDs
@app.route("/process_data")
def process_data(request):
    tx_id = request.headers.get("MCP-Tx-Transaction-ID")
    logger.info(f"Processing data for transaction {tx_id}")
    
    # Now you can trace end-to-end: client → server → database → external APIs
    return {"result": "processed", "transaction_id": tx_id}
```

**Result**: When users report issues, one transaction ID traces the entire flow across all systems.

### ⚡ Advanced Capabilities Unlocked

- **Async task support**: ACK immediately, process in background, client polls for results
- **Request cancellation**: Client can cancel long-running operations
- **Load-aware retry**: Server can tell client "retry in 30 seconds" during high load

## Technical Architecture

MCP-Tx provides a decorator-based API that sits on top of the core MCP-Tx reliability layer:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   MCP-Tx App     │────▶│   MCP-Tx Session │────▶│   MCP Session    │────▶│    Tool     │
│  @app.tool()     │◀────│  (Reliability)   │◀────│   (Standard)     │◀────│  (Server)   │
└──────────────────┘     └──────────────────┘     └──────────────────┘     └─────────────┘
       │                          │
       │                          ▼
       │                  ┌──────────────────┐
       │                  │   Reliability    │
       │                  │ • ACK tracking   │
       │                  │ • Retry logic    │ 
       │                  │ • Deduplication  │
       │                  │ • Timeouts       │
       └─────────────────▶│ • Input validation│
                          └──────────────────┘
```

## Advanced Usage

### Custom Retry Policies

```python
@app.tool(retry_policy=RetryPolicy(
    max_attempts=5,
    base_delay_ms=1000,  # 1 second base delay
    backoff_multiplier=2.0,  # Exponential backoff
    jitter=True  # Add randomness to prevent thundering herd
))
async def critical_operation(data: dict) -> dict:
    """Critical operation with custom retry logic."""
    return await process_critical_data(data)
```

### Custom Idempotency Keys

```python
@app.tool(
    idempotency_key_generator=lambda args: f"user-{args['user_id']}-{args['action']}"
)
async def user_operation(user_id: str, action: str, data: dict) -> dict:
    """User operation with custom idempotency key."""
    return await execute_user_action(user_id, action, data)
```

## Real-World Use Cases

### 🤝 **Human-in-the-Loop Workflows**

**Content moderation workflow** with human oversight:
```python
# Step 1: AI analyzes content
content_analysis = await app.call_tool("analyze_content", {"text": user_post})

# Step 2: If flagged, get human review
if content_analysis.result["needs_review"]:
    human_decision = await app.call_tool("human_content_review", {
        "content": user_post,
        "ai_analysis": content_analysis.result,
        "timeout_ms": 1800000  # 30 minutes
    })
    
    # Step 3: Take action based on human decision
    if human_decision.mcp_tx_meta.ack and human_decision.result["action"] == "approve":
        await app.call_tool("publish_content", {"post_id": post_id})
```

**Financial approval workflow** with multiple stakeholders:
```python
# Automatic compliance check
compliance = await app.call_tool("compliance_check", {"transaction": tx_data})

if compliance.result["amount"] > 10000:
    # Requires manager approval
    manager_approval = await app.call_tool("manager_approval", {
        "transaction": tx_data,
        "compliance_report": compliance.result
    })
    
    if manager_approval.mcp_tx_meta.ack:
        await app.call_tool("process_transaction", {"transaction_id": tx_id})
```

### 🚀 **Ready-to-Run Applications**
- **[Smart Research Assistant Web App](examples/)** - Human-approved AI research with Streamlit UI
  ```bash
  uv run python examples/run_frontend.py  # Launch web interface
  ```
- **[Basic Reliability Example](examples/fastmcp_tx_example.py)** - Complete working example

### 🏢 **Enterprise Integration Patterns**

**Approval Systems**: Human approval steps in automated workflows  
**Content Pipelines**: AI processing with human quality control  
**Financial Processing**: Automated checks with human oversight for high-value transactions  
**Customer Support**: AI triage with human escalation paths

### 🔗 **Framework Integrations**  
- **[Flask Integration](../docs/en/examples/integration.md#flask-integration)** - Web framework integration  
- **[Celery Integration](../docs/en/examples/integration.md#celery-integration)** - Background task processing
- **[AWS Lambda](../docs/en/examples/integration.md#aws-lambda-integration)** - Serverless deployment

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests with coverage
uv run pytest tests/ -v --cov=src/mcp_tx

# Format code
uv run ruff format .

# Type check
uv run pyright

# Run linter
uv run ruff check src/ tests/
```

**Test Coverage**: 31 test cases covering edge cases, concurrency, input validation, and error handling.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite: `uv run pytest`
5. Submit a pull request

## License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.

## Related Projects

- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)** - The underlying MCP implementation
- **[FastMCP](https://github.com/jlowin/fastmcp)** - FastAPI-style decorators for MCP servers

---

## Vision: The Reliable AI Ecosystem

**MCP-Tx transforms AI development from "hope it works" to "guaranteed to work."**

By treating humans, AI agents, and tools as unified "servers" in a reliable ecosystem, MCP-Tx enables:

- 🌐 **Hybrid intelligence workflows** where AI and humans seamlessly collaborate
- 🛡️ **Production-grade reliability** for mission-critical AI applications  
- 💰 **Cost-effective operations** through intelligent deduplication and retry
- 🔍 **Complete observability** with end-to-end tracing across all interactions

**MCP opened the door to tools. MCP-Tx ensures you can trust every step of the journey.**