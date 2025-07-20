# RMCP Python SDK

[![Tests](https://github.com/Daku-on/reliable-MCP-draft/actions/workflows/test.yml/badge.svg)](https://github.com/Daku-on/reliable-MCP-draft/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

> **Production-ready Python SDK for Reliable Model Context Protocol (RMCP)**  
> Add delivery guarantees, automatic retry, and request deduplication to any MCP session.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Daku-on/reliable-MCP-draft.git
cd reliable-MCP-draft/rmcp-python

# Install dependencies
uv install

# Run tests
uv run pytest tests/ -v
```

### Basic Usage

```python
from rmcp import FastRMCP, RetryPolicy
from mcp.client.session import ClientSession

# Wrap your existing MCP session
app = FastRMCP(mcp_session)

@app.tool()
async def reliable_file_writer(path: str, content: str) -> dict:
    """Write file with automatic retry and idempotency."""
    with open(path, 'w') as f:
        f.write(content)
    return {"path": path, "size": len(content)}

# Use with automatic RMCP reliability
async with app:
    result = await app.call_tool("reliable_file_writer", {
        "path": "/tmp/data.json", 
        "content": json.dumps(data)
    })
    
    print(f"ACK: {result.rmcp_meta.ack}")           # True - confirmed receipt
    print(f"Processed: {result.rmcp_meta.processed}") # True - actually executed  
    print(f"Attempts: {result.rmcp_meta.attempts}")    # How many retries needed
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
- [**Architecture Overview**](../docs/en/architecture.md) - How RMCP enhances MCP
- [**API Reference**](../docs/en/api/rmcp-session.md) - Detailed API documentation
- [**Examples**](../docs/en/examples/basic.md) - Common usage patterns
- [**Advanced Examples**](../docs/en/examples/advanced.md) - Complex workflows and integrations

## Architecture

FastRMCP provides a decorator-based API that sits on top of the core RMCP reliability layer:

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   FastRMCP App   │────▶│   RMCP Session   │────▶│   MCP Session    │────▶│    Tool     │
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

## Examples

- **[Basic Example](examples/fastrmcp_example.py)** - Complete working example
- **[Flask Integration](../docs/en/examples/integration.md#flask-integration)** - Web framework integration  
- **[Celery Integration](../docs/en/examples/integration.md#celery-integration)** - Background task processing
- **[AWS Lambda](../docs/en/examples/integration.md#aws-lambda-integration)** - Serverless deployment

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests with coverage
uv run pytest tests/ -v --cov=src/rmcp

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

**MCP opened the door to tools. RMCP makes sure you can trust what happened next.**