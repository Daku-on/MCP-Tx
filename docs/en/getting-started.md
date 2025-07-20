# Getting Started with MCP-Tx

Get up and running with the Reliable Model Context Protocol (MCP-Tx) Python SDK in 5 minutes.

## What is MCP-Tx?

MCP-Tx is a **reliability layer** that wraps existing MCP (Model Context Protocol) sessions to provide:

- 🔒 **Guaranteed delivery** - ACK/NACK for every tool call
- 🔄 **Automatic retry** - Exponential backoff with jitter  
- 🚫 **Deduplication** - Idempotency keys prevent duplicate execution
- 📊 **Transaction tracking** - Full lifecycle visibility
- ✅ **100% MCP compatible** - Drop-in replacement

## Installation

### Requirements
- Python 3.10+
- Existing MCP setup (client and server)

### Install MCP-Tx

```bash
# Using uv (recommended)
uv add mcp_tx

# Using pip
pip install mcp_tx
```

### Development Installation

```bash
git clone https://github.com/Daku-on/reliable-MCP-draft
cd reliable-MCP-draft/rmcp-python
uv sync --dev
```

## 5-Minute Quick Start

### Step 1: Import MCP-Tx

```python
import asyncio
from rmcp import MCP-TxSession, MCP-TxConfig, RetryPolicy
from mcp.client.session import ClientSession  # Your existing MCP client
```

### Step 2: Wrap Your MCP Session

```python
async def main():
    # Your existing MCP session setup
    mcp_session = ClientSession(...)  # Configure as usual
    
    # Wrap with MCP-Tx for reliability
    rmcp_session = MCP-TxSession(mcp_session)
    
    # Initialize (handles capability negotiation)
    await rmcp_session.initialize()
```

### Step 3: Enhanced Tool Calls

```python
    # Simple tool call with automatic reliability
    result = await rmcp_session.call_tool(
        "file_reader",
        {"path": "/path/to/file.txt"}
    )
    
    # Check reliability guarantees
    print(f"✅ Acknowledged: {result.ack}")
    print(f"✅ Processed: {result.processed}")  
    print(f"📊 Attempts: {result.attempts}")
    print(f"🎯 Status: {result.final_status}")
    
    # Access the actual result
    if result.ack:
        print(f"📄 Content: {result.result}")
```

### Step 4: Advanced Features

```python
    # Tool call with idempotency (prevents duplicates)
    result = await rmcp_session.call_tool(
        "file_writer",
        {"path": "/path/to/output.txt", "content": "Hello World"},
        idempotency_key="write-hello-v1"  # Unique key
    )
    
    # Tool call with custom retry policy
    custom_retry = RetryPolicy(
        max_attempts=5,
        base_delay_ms=500,
        backoff_multiplier=2.0,
        jitter=True
    )
    
    result = await rmcp_session.call_tool(
        "api_caller",
        {"url": "https://api.example.com/data"},
        retry_policy=custom_retry,
        timeout_ms=10000  # 10 seconds
    )
    
    # Clean up
    await rmcp_session.close()

# Run the example
asyncio.run(main())
```

## Complete Working Example

```python
import asyncio
import logging
from rmcp import MCP-TxSession, MCP-TxConfig, RetryPolicy

# Mock MCP session for demonstration
class MockMCPSession:
    async def initialize(self, **kwargs):
        # Mock server with MCP-Tx support
        class MockResult:
            class capabilities:
                experimental = {"rmcp": {"version": "0.1.0"}}
        return MockResult()
    
    async def send_request(self, request):
        # Mock successful tool execution
        return {
            "result": {
                "content": [{"type": "text", "text": "Tool executed successfully!"}]
            }
        }

async def complete_example():
    """Complete working example with error handling."""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create mock MCP session (replace with real MCP session)
    mcp_session = MockMCPSession()
    
    # Configure MCP-Tx with custom settings
    config = MCP-TxConfig(
        default_timeout_ms=5000,
        retry_policy=RetryPolicy(
            max_attempts=3,
            base_delay_ms=1000,
            backoff_multiplier=2.0,
            jitter=True
        ),
        max_concurrent_requests=10
    )
    
    # Create MCP-Tx session
    async with MCP-TxSession(mcp_session, config) as rmcp:
        await rmcp.initialize()
        
        print(f"🚀 MCP-Tx enabled: {rmcp.rmcp_enabled}")
        
        # Example 1: Basic tool call
        print("\\n📝 Example 1: Basic tool call")
        result = await rmcp.call_tool("echo", {"message": "Hello MCP-Tx!"})
        print(f"   Result: {result.result}")
        print(f"   Status: {result.final_status}")
        
        # Example 2: Idempotent operation
        print("\\n🔒 Example 2: Idempotent operation") 
        for i in range(3):
            result = await rmcp.call_tool(
                "create_user",
                {"name": "Alice", "email": "alice@example.com"},
                idempotency_key="create-alice-v1"
            )
            print(f"   Call {i+1}: Duplicate={result.rmcp_meta.duplicate}")
        
        # Example 3: Custom retry policy
        print("\\n🔄 Example 3: Custom retry policy")
        aggressive_retry = RetryPolicy(max_attempts=5, base_delay_ms=200)
        result = await rmcp.call_tool(
            "unreliable_api",
            {"endpoint": "/data"},
            retry_policy=aggressive_retry
        )
        print(f"   Attempts: {result.attempts}")
        print(f"   Success: {result.ack}")

if __name__ == "__main__":
    asyncio.run(complete_example())
```

## What's Next?

### Learn Core Concepts
- [Architecture Overview](architecture.md) - Understand how MCP-Tx works
- [Architecture Overview](architecture.md) - Deep dive into MCP-Tx reliability features
- [API Reference](api/rmcp-session.md) - Detailed API documentation

### Explore Examples
- [Basic Usage Examples](examples/basic.md) - Common patterns and use cases
- [Migration Guide](migration.md) - Step-by-step upgrade from plain MCP
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### Migration from MCP
- [Migration Guide](migration.md) - Step-by-step upgrade from plain MCP
- [FAQ](faq.md) - Frequently asked questions

## Need Help?

- 📖 Check the [FAQ](faq.md) for common questions
- 🐛 Review [Troubleshooting](troubleshooting.md) for issues
- 💬 [Open an issue](https://github.com/Daku-on/reliable-MCP-draft/issues) on GitHub
- 📧 Read the [API Reference](api/rmcp-session.md) for detailed documentation

---

**Next**: [Basic Usage Examples](examples/basic.md) →