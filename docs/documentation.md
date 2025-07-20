# MCP-Tx Python SDK Documentation

MCP-Tx (Reliable Model Context Protocol) is a reliability layer that wraps existing MCP sessions to provide delivery guarantees, automatic retry, request deduplication, and enhanced error handling.

## Installation

```bash
# Using uv (recommended)
uv add mcp_tx

# Using pip
pip install mcp_tx
```

## Quick Start

```python
import asyncio
from mcp_tx import MCP_TxSession
from mcp.client.session import ClientSession

async def main():
    # Mock MCP session
    class MockMCPSession:
        async def initialize(self, **kwargs):
            class MockResult:
                class capabilities:
                    experimental = {"mcp_tx": {"version": "0.1.0"}}
            return MockResult()
        async def send_request(self, request):
            return {"result": {"status": "ok"}}

    mcp_session = MockMCPSession()
    
    async with MCP_TxSession(mcp_session) as mcp_tx_session:
        await mcp_tx_session.initialize()
        result = await mcp_tx_session.call_tool("file_reader", {"path": "/path/to/file.txt"})
        
        if result.ack:
            print(f"✅ Tool call acknowledged and processed.")
            print(f"   Result: {result.result}")
            print(f"   Attempts: {result.attempts}")
        else:
            print(f"❌ Tool call failed: {result.mcp_tx_meta.error_message}")

asyncio.run(main())
```

# Getting Started

## Complete Working Example

```python
import asyncio
import logging
from mcp_tx import MCP_TxSession, MCP_TxConfig, RetryPolicy

class MockMCPSession:
    async def initialize(self, **kwargs):
        class MockResult:
            class capabilities:
                experimental = {"mcp_tx": {"version": "0.1.0"}}
        return MockResult()
    
    async def send_request(self, request):
        return {"result": {"content": [{"type": "text", "text": "Tool executed!"}]}}

async def complete_example():
    logging.basicConfig(level=logging.INFO)
    mcp_session = MockMCPSession()
    config = MCP_TxConfig(default_timeout_ms=5000)
    
    async with MCP_TxSession(mcp_session, config) as mcp_tx:
        await mcp_tx.initialize()
        print(f"🚀 MCP-Tx enabled: {mcp_tx.mcp_tx_enabled}")
        
        result = await mcp_tx.call_tool("echo", {"message": "Hello MCP-Tx!"})
        print(f"   Result: {result.result}")
```

# Architecture

### MCP_TxSession (Wrapper)

```python
class MCP_TxSession:
    def __init__(self, mcp_session: BaseSession, config: MCP_TxConfig = None):
        self.mcp_session = mcp_session
        self.config = config or MCP_TxConfig()
```

### Message Enhancement

```json
{
  "method": "tools/call",
  "params": {
    "name": "file_reader",
    "arguments": {"path": "/data.txt"},
    "_meta": {
      "mcp_tx": {
        "version": "0.1.0",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "idempotency_key": "read_data_v1",
        "expect_ack": true
      }
    }
  }
}
```

# Reliability Features

## Core Guarantees

### ACK/NACK Acknowledgments

```python
result = await mcp_tx_session.call_tool("my_tool", {})
if result.mcp_tx_meta.ack:
    print("Tool acknowledged receipt")
```

### Automatic Retry with Exponential Backoff

```python
from mcp_tx import RetryPolicy
retry_policy = RetryPolicy(max_attempts=5, base_delay_ms=1000)
result = await mcp_tx_session.call_tool("unreliable_api", {}, retry_policy=retry_policy)
```

### Request Deduplication

```python
result = await mcp_tx_session.call_tool("create_user", {}, idempotency_key="create-user-123")
```

# Configuration Guide

## Quick Start Configuration

```python
from mcp_tx import MCPTxConfig, MCPTxSession
# Basic
config = MCPTxConfig()
session = MCPTxSession(mcp_session, config)

# Customized
config = MCPTxConfig(
    default_timeout_ms=30000,
    max_concurrent_requests=10,
    retry_policy=RetryPolicy(max_attempts=3)
)
```

# API Reference

## Class: MCPTxSession

### Constructor
`__init__(self, mcp_session: BaseSession, config: MCPTxConfig | None = None)`

### Methods
- `initialize(self, **kwargs) -> Any`
- `call_tool(self, name: str, arguments: dict, *, idempotency_key: str | None = None, timeout_ms: int | None = None, retry_policy: RetryPolicy | None = None) -> MCPTxResult`
- `close(self) -> None`

### Properties
- `mcp_tx_enabled: bool`
- `active_requests: dict`

## Dataclass: MCPTxResult
- `result: Any`
- `mcp_tx_meta: MCPTxResponse`

# Usage Examples

## Basic Examples

### File Operations and API Calls

```python
# Idempotent file write
await mcp_tx.call_tool(
    "file_writer",
    {"path": "/output.txt", "content": "..."},
    idempotency_key="write-output-v1"
)

# API call with automatic retry
await mcp_tx.call_tool(
    "http_client",
    {"method": "GET", "url": "https://api.example.com/data"},
    timeout_ms=15000
)
```

## Advanced Examples

### Multi-Step Workflows and Circuit Breakers

```python
# Workflow combining multiple reliability features
class WorkflowManager:
    async def execute_data_pipeline(self, url: str):
        # ... Step 1: Download (with retry)
        # ... Step 2: Validate
        # ... Step 3: Process (with custom retry)
        pass

# Circuit breaker for sensitive calls
breaker = CircuitBreaker()
@app.tool()
async def protected_api_call(endpoint: str):
    return await breaker.call(external_api_call, endpoint)
```

## Framework Integrations

### FastAPI, Django, and Celery

```python
# FastAPI
@app.post("/process")
async def process_file(mcp_tx: MCPTxSession = Depends(get_mcp_tx_session)):
    result = await mcp_tx.call_tool(...)

# Django (using async_to_sync)
result = async_to_sync(request.rmcp.call_tool)(...)

# Celery (with a custom Task class)
@app.task(base=MCP_TxTask)
def process_data_async(self, data_id: str):
    result = loop.run_until_complete(self.rmcp.call_tool(...))
```

## Building AI Agents

Leverage MCP-Tx features like retry, idempotency, and transaction tracking to build reliable AI agents.

```python
# Example of a Smart Research Assistant
class SmartResearchAssistant:
    async def conduct_research(self, query: str):
        # Step 1: Web Search (with retry)
        # Step 2: Content Analysis (idempotent)
        # Step 3: Fact Checking
        # Step 4: Report Generation
        pass
```

# Migration Guide

## Migration Strategies

### Drop-in Replacement

**Before (MCP):**
```python
result = await session.call_tool("file_reader", {"path": "/data.txt"})
```

**After (MCP-Tx):**
```python
mcp_tx_session = MCPTxSession(mcp_session)
await mcp_tx_session.initialize()
result = await mcp_tx_session.call_tool("file_reader", {"path": "/data.txt"})
if result.ack:
    actual_result = result.result
```

# Frequently Asked Questions (FAQ)

### What is MCP-Tx?
It's a backward-compatible reliability layer for existing MCP sessions.

### Do I need to modify my MCP server?
No. MCP-Tx is a client-side layer and works with any standard MCP server.

### Can I use it with my existing MCP library?
Yes. It wraps any object that implements the MCP session interface.
