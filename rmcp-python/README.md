# RMCP Python SDK

Reliable Model Context Protocol (RMCP) Python implementation - A reliability layer for MCP tool calls.

## Features

- **ACK/NACK guarantees**: Explicit acknowledgment for every tool call
- **Automatic retry**: Configurable retry policies with exponential backoff
- **Request deduplication**: Idempotency keys prevent duplicate execution
- **Transaction tracking**: Full lifecycle management for multi-step operations
- **100% MCP compatible**: Transparent fallback to standard MCP

## Quick Start

```python
import asyncio
from rmcp import RMCPSession
from mcp.client.session import ClientSession

async def main():
    # Wrap any existing MCP session
    mcp_session = ClientSession(...)  # Your existing MCP setup
    rmcp_session = RMCPSession(mcp_session)
    
    # Enhanced tool calls with reliability guarantees
    result = await rmcp_session.call_tool(
        "file_writer", 
        {"path": "/tmp/data.json", "content": "test"}
    )
    
    # Check execution guarantees
    print(f"Acknowledged: {result.ack}")
    print(f"Processed: {result.processed}")
    print(f"Status: {result.final_status}")
    print(f"Retry attempts: {result.attempts}")

asyncio.run(main())
```

## Installation

```bash
# From PyPI (when published)
uv add rmcp

# For development
git clone https://github.com/reliable-mcp-draft/rmcp-python
cd rmcp-python
uv sync --dev
```

## Development

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Type check
uv run pyright
```

## Architecture

RMCP wraps existing MCP sessions without breaking changes:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Agent     │────▶│   RMCP Wrapper   │────▶│    Tool     │
│  (Client)   │◀────│  + MCP Session   │◀────│  (Server)   │
└─────────────┘     └──────────────────┘     └─────────────┘
```

## License

Apache 2.0 License - see LICENSE file for details.