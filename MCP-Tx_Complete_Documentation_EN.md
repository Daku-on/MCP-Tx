# MCP-Tx (Model Context Protocol with Transactions) - Complete Documentation

**Version**: 0.1.0 (Production MVP)  
**Last Updated**: January 2025  
**Language**: English

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Architecture Overview](#architecture-overview)
4. [Compatibility Guide](#compatibility-guide)
5. [Configuration Reference](#configuration-reference)
6. [Reliability Features](#reliability-features)
7. [Performance Optimization](#performance-optimization)
8. [Migration from MCP](#migration-from-mcp)
9. [Building AI Agents](#building-ai-agents)
10. [API Reference](#api-reference)
11. [Usage Examples](#usage-examples)
    - [Basic Examples](#basic-examples)
    - [Advanced Examples](#advanced-examples)
    - [Integration Examples](#integration-examples)
12. [FAQ](#faq)
13. [Troubleshooting](#troubleshooting)

---

## Introduction

# MCP-Tx Python SDK Documentation

Comprehensive documentation for the MCP-Tx Python SDK.

## 📚 Documentation Index

### Getting Started
- [**Quick Start Guide**](getting-started.md) - Get up and running in 5 minutes

### Core Concepts
- [**Architecture Overview**](architecture.md) - How MCP-Tx enhances MCP

### API Reference
- [**MCP_TxSession**](api/mcp-tx-session.md) - Main client interface

### Usage Examples
- [**Basic Examples**](examples/basic.md) - Simple tool calls and error handling
- [**AI Agents**](ai-agents.md) - Building reliable AI agents with MCP-Tx

### Migration & Compatibility
- [**Migration from MCP**](migration.md) - Step-by-step upgrade guide

### Operations & Troubleshooting
- [**Troubleshooting**](troubleshooting.md) - Common issues and solutions
- [**FAQ**](faq.md) - Frequently asked questions

## 🎯 Quick Navigation

### For New Users
1. [Getting Started](getting-started.md) → [Examples](examples/basic.md)

### For MCP Users  
1. [Migration Guide](migration.md) → [Examples](examples/basic.md)

### For Developers
1. [Architecture](architecture.md) → [API Reference](api/mcp-tx-session.md)

## 🔗 External Resources

- [MCP-Tx Specification](../../../mvp-spec.md) - Protocol specification
- [Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) - Underlying MCP implementation
- [GitHub Repository](https://github.com/Daku-on/MCP-Tx) - Source code and issues

## 📝 Contributing

Found an issue with the documentation? Please [open an issue](https://github.com/Daku-on/MCP-Tx/issues) or submit a pull request.

---

**Last Updated**: Session 1 completion - Production-ready MVP with 93% test coverage

---

## Getting Started

# Getting Started with MCP-Tx

Get up and running with the MCP-Tx (Reliable Model Context Protocol) Python SDK in 5 minutes.

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
git clone https://github.com/Daku-on/MCP-Tx
cd MCP-Tx/mcp_tx-python
uv sync --dev
```

## 5-Minute Quick Start

### Step 1: Import MCP-Tx

```python
import asyncio
from mcp_tx import MCPTxSession, MCPTxConfig, RetryPolicy
from mcp.client.session import ClientSession  # Your existing MCP client
```

### Step 2: Wrap Your MCP Session

```python
async def main():
    # Your existing MCP session setup
    mcp_session = ClientSession(...)  # Configure as usual
    
    # Wrap with MCP-Tx for reliability
    mcp_tx_session = MCPTxSession(mcp_session)
    
    # Initialize (handles capability negotiation)
    await mcp_tx_session.initialize()
```

### Step 3: Enhanced Tool Calls

```python
    # Simple tool call with automatic reliability
    result = await mcp_tx_session.call_tool(
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
    result = await mcp_tx_session.call_tool(
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
    
    result = await mcp_tx_session.call_tool(
        "api_caller",
        {"url": "https://api.example.com/data"},
        retry_policy=custom_retry,
        timeout_ms=10000  # 10 seconds
    )
    
    # Clean up
    await mcp_tx_session.close()

# Run the example
asyncio.run(main())
```

## Complete Working Example

```python
import asyncio
import logging
from mcp_tx import MCPTxSession, MCPTxConfig, RetryPolicy

# Mock MCP session for demonstration
class MockMCPSession:
    async def initialize(self, **kwargs):
        # Mock server with MCP-Tx support
        class MockResult:
            class capabilities:
                experimental = {"mcp_tx": {"version": "0.1.0"}}
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
    config = MCPTxConfig(
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
    async with MCPTxSession(mcp_session, config) as mcp_tx:
        await mcp_tx.initialize()
        
        print(f"🚀 MCP-Tx enabled: {mcp_tx.mcp_tx_enabled}")
        
        # Example 1: Basic tool call
        print("\n📝 Example 1: Basic tool call")
        result = await mcp_tx.call_tool("echo", {"message": "Hello MCP-Tx!"})
        print(f"   Result: {result.result}")
        print(f"   Status: {result.final_status}")
        
        # Example 2: Idempotent operation
        print("\n🔒 Example 2: Idempotent operation") 
        for i in range(3):
            result = await mcp_tx.call_tool(
                "create_user",
                {"name": "Alice", "email": "alice@example.com"},
                idempotency_key="create-alice-v1"
            )
            print(f"   Call {i+1}: Duplicate={result.mcp_tx_meta.duplicate}")
        
        # Example 3: Custom retry policy
        print("\n🔄 Example 3: Custom retry policy")
        aggressive_retry = RetryPolicy(max_attempts=5, base_delay_ms=200)
        result = await mcp_tx.call_tool(
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
- [Architecture Overview](#architecture-overview) - Understand how MCP-Tx works
- [API Reference](#api-reference) - Detailed API documentation

### Explore Examples
- [Basic Usage Examples](#basic-examples) - Common patterns and use cases
- [Migration Guide](#migration-from-mcp) - Step-by-step upgrade from plain MCP
- [Troubleshooting](#troubleshooting) - Common issues and solutions

### Migration from MCP
- [Migration Guide](#migration-from-mcp) - Step-by-step upgrade from plain MCP
- [FAQ](#faq) - Frequently asked questions

## Need Help?

- 📖 Check the [FAQ](#faq) for common questions
- 🐛 Review [Troubleshooting](#troubleshooting) for issues
- 💬 [Open an issue](https://github.com/Daku-on/MCP-Tx/issues) on GitHub
- 📧 Read the [API Reference](#api-reference) for detailed documentation

---

## Architecture Overview

# MCP-Tx Architecture Overview

Understanding how MCP-Tx enhances MCP with reliability guarantees.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│                 │    │                      │    │                 │
│   Your Client   │    │    MCP-Tx Session   │    │   MCP Server    │
│   Application   │    │   (Reliability       │    │   (Existing)    │
│                 │    │    Wrapper)          │    │                 │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
         │                        │                          │
         │ call_tool()            │ Enhanced MCP             │ Standard MCP  
         ├─────────────────────▶  │ with _meta.mcp_tx        ├──────────────▶
         │                        │                          │
         │ MCPTxResult            │ Standard MCP             │ Tool Result
         ◀─────────────────────── │ Response                 ◀──────────────┤
         │                        │                          │
```

## Core Components

### 1. MCPTxSession (Wrapper)

The main interface that wraps any existing MCP session:

```python
class MCPTxSession:
    def __init__(self, mcp_session: BaseSession, config: MCPTxConfig = None):
        self.mcp_session = mcp_session  # Your existing MCP session
        self.config = config or MCPTxConfig()
        # ... reliability infrastructure
```

**Key Responsibilities**:
- ✅ Capability negotiation with servers
- ✅ Request ID generation and tracking
- ✅ ACK/NACK handling  
- ✅ Retry logic with exponential backoff
- ✅ Idempotency-based deduplication
- ✅ Transaction lifecycle management
- ✅ Transparent fallback to standard MCP

### 2. Message Enhancement

MCP-Tx enhances standard MCP messages with reliability metadata:

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
        "transaction_id": "txn_123456789",
        "idempotency_key": "read_data_v1",
        "expect_ack": true,
        "retry_count": 0,
        "timeout_ms": 30000,
        "timestamp": "2024-01-15T10:30:00Z"
      }
    }
  }
}
```

### 3. Request Lifecycle

```
Request Created
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   PENDING   │───▶│     SENT     │───▶│ ACKNOWLEDGED│
└─────────────┘    └──────────────┘    └─────────────┘
      │                     │                   │
      │            ┌────────▼────────┐          │
      │            │     FAILED      │          │
      ▼            └─────────────────┘          ▼
┌─────────────┐              │             ┌─────────────┐
│   TIMEOUT   │              │             │  COMPLETED  │
└─────────────┘              │             └─────────────┘
      │                      │                   │
      └──────────────────────┼───────────────────┘
                             ▼
                    ┌─────────────────┐
                    │   RETRY LOGIC   │
                    │ (if retryable)  │
                    └─────────────────┘
```

## Reliability Features Deep Dive

### 1. ACK/NACK Mechanism

**Acknowledgment Flow**:
```python
# Client sends request with expect_ack=true
request = {
    "_meta": {"mcp_tx": {"expect_ack": True, ...}},
    ...
}

# Server processes and responds with ACK
response = {
    "result": {...},
    "_meta": {
        "mcp_tx": {
            "ack": True,           # Explicit acknowledgment
            "processed": True,     # Tool was executed
            "request_id": "...",   # Correlation
        }
    }
}

# Client validates ACK and returns MCPTxResult
```

### 2. Retry Logic with Exponential Backoff

```python
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 1000
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: list[str] = [
        "CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR", "TEMPORARY_FAILURE"
    ]

def calculate_delay(attempt: int, policy: RetryPolicy) -> int:
    # Base delay * multiplier^attempt
    delay = policy.base_delay_ms * (policy.backoff_multiplier ** attempt)
    delay = min(delay, policy.max_delay_ms)
    
    if policy.jitter:
        # Add ±20% jitter to prevent thundering herd
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay = int(delay + jitter)
    
    return max(delay, policy.base_delay_ms)
```

### 3. Idempotency and Deduplication

**Cache-based Deduplication**:
```python
class MCPTxSession:
    def __init__(self):
        # LRU cache with TTL for memory safety
        self._deduplication_cache: dict[str, tuple[MCPTxResult, datetime]] = {}
    
    def _get_cached_result(self, idempotency_key: str) -> MCPTxResult | None:
        if idempotency_key in self._deduplication_cache:
            cached_result, timestamp = self._deduplication_cache[idempotency_key]
            
            # Check TTL (default: 5 minutes)
            if timestamp + timedelta(milliseconds=self.config.deduplication_window_ms) > datetime.utcnow():
                # Return copy with duplicate=True
                return self._create_duplicate_response(cached_result)
            else:
                # Expired, remove from cache
                del self._deduplication_cache[idempotency_key]
        
        return None
```

### 4. Concurrent Request Management

```python
class MCPTxSession:
    def __init__(self, config: MCPTxConfig):
        # Semaphore for concurrency control
        self._request_semaphore = anyio.Semaphore(config.max_concurrent_requests)
        
        # Active request tracking
        self._active_requests: dict[str, RequestTracker] = {}
    
    async def call_tool(self, ...):
        # Acquire semaphore before processing
        async with self._request_semaphore:
            return await self._call_tool_with_retry(...)
```

## Capability Negotiation

MCP-Tx uses MCP's experimental capabilities to negotiate features:

### Client Advertisement
```python
# During initialization, MCP-Tx advertises its capabilities
kwargs["capabilities"]["experimental"]["mcp_tx"] = {
    "version": "0.1.0",
    "features": ["ack", "retry", "idempotency", "transactions"]
}
```

### Server Response
```python
# Server responds with supported MCP-Tx features
server_capabilities = {
    "experimental": {
        "mcp_tx": {
            "version": "0.1.0", 
            "features": ["ack", "retry"]  # Subset of client features
        }
    }
}
```

### Fallback Behavior
```python
if not self._mcp_tx_enabled:
    # Transparent fallback to standard MCP
    return await self._execute_standard_mcp_call(name, arguments, timeout_ms)
else:
    # Enhanced MCP with MCP-Tx metadata
    return await self._execute_mcp_tx_call(name, arguments, mcp_tx_meta, timeout_ms)
```

## Performance Characteristics

### Memory Usage
- **Request Tracking**: O(concurrent_requests) - typically 10-100 requests
- **Deduplication Cache**: O(unique_idempotency_keys) with TTL-based eviction
- **Configuration**: Minimal overhead (~1KB per session)

### Latency Impact
- **MCP-Tx Overhead**: < 1ms per request (metadata processing)
- **Network Overhead**: +200-500 bytes per request (MCP-Tx metadata)
- **Retry Delays**: Configurable exponential backoff (default: 1s, 2s, 4s)

### Throughput
- **Concurrent Requests**: Configurable limit (default: 10)
- **Rate Limiting**: Optional (not implemented in MVP)
- **Async Performance**: Native anyio support for high concurrency

## Error Handling Strategy

### Error Classification
```python
class MCPTxError(Exception):
    def __init__(self, message: str, error_code: str, retryable: bool):
        self.retryable = retryable  # Determines retry behavior

# Specific error types
MCPTxTimeoutError(retryable=True)    # Retry on timeout
MCPTxNetworkError(retryable=True)    # Retry on network issues  
MCPTxSequenceError(retryable=False)  # Don't retry on sequence errors
```

### Error Propagation
1. **Transient Errors**: Automatic retry with backoff
2. **Permanent Errors**: Immediate failure, no retry
3. **Unknown Errors**: Configurable retry behavior

## Security Considerations

### Request ID Generation
```python
# Cryptographically secure UUID generation
request_id = str(uuid.uuid4())  # Prevents ID prediction/collision
```

### Error Message Sanitization
```python
def _sanitize_error_message(self, error: Exception) -> str:
    # Remove sensitive information from error messages
    patterns = [
        r"password[=:]\s*\S+", r"token[=:]\s*\S+", 
        r"key[=:]\s*\S+", r"/Users/[^/\s]+", r"/home/[^/\s]+"
    ]
    # ... sanitization logic
```

### Capability Validation
- Server capabilities are validated during negotiation
- Unknown/unsafe features are ignored
- Graceful degradation for unsupported features

---

*[Note: Due to length constraints, I'll continue with the rest of the documentation sections in subsequent responses. The complete documentation would include all sections: Compatibility Guide, Configuration Reference, Reliability Features, Performance Optimization, Migration Guide, AI Agents, API Reference, Usage Examples, FAQ, and Troubleshooting.]*

---

**This is Part 1 of the Complete English Documentation. The document continues with additional sections for full coverage.**