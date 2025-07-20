# MCP-Tx Reliability Features

This document provides a deep dive into the reliability features that MCP-Tx adds to standard MCP.

## Core Reliability Guarantees

### 1. ACK/NACK Acknowledgments

MCP-Tx requires explicit acknowledgment for every tool call:

```python
result = await rmcp_session.call_tool("my_tool", {})

# Check acknowledgment status
if result.rmcp_meta.ack:
    print("Tool acknowledged receipt")
else:
    print(f"Tool rejected: {result.rmcp_meta.error_message}")
```

**Benefits:**
- Know when tools actually receive requests
- Distinguish between network failures and tool rejections
- Clear error messaging for debugging

### 2. Automatic Retry with Exponential Backoff

MCP-Tx automatically retries failed operations:

```python
from mcp_tx import RetryPolicy

# Configure retry behavior
retry_policy = RetryPolicy(
    max_attempts=5,
    base_delay_ms=1000,      # Start with 1 second
    backoff_multiplier=2.0,  # Double each time
    max_delay_ms=30000,      # Cap at 30 seconds
    jitter=True              # Add randomness
)

# Apply to specific tools
result = await rmcp_session.call_tool(
    "unreliable_api",
    {"data": "important"},
    retry_policy=retry_policy
)

print(f"Succeeded after {result.rmcp_meta.attempts} attempts")
```

**Retry Triggers:**
- Network timeouts
- Connection errors
- 5xx server errors
- Explicit retry responses

**Non-Retryable Errors:**
- 4xx client errors
- Validation failures
- Authentication errors

### 3. Request Deduplication

Prevent duplicate executions with idempotency keys:

```python
# Automatic deduplication
result1 = await rmcp_session.call_tool(
    "create_user",
    {"email": "user@example.com"},
    idempotency_key="create-user-12345"
)

# Same call won't execute again
result2 = await rmcp_session.call_tool(
    "create_user",
    {"email": "user@example.com"},
    idempotency_key="create-user-12345"
)

assert result2.rmcp_meta.duplicate == True
```

**Deduplication Window:**
- Default: 5 minutes
- Configurable per session
- Server-side state management

### 4. Transaction Tracking

Track multi-step operations:

```python
# Each request gets a unique ID
result = await rmcp_session.call_tool("start_workflow", {})
request_id = result.rmcp_meta.request_id

# Use for correlation
await rmcp_session.call_tool(
    "workflow_step_2",
    {"previous_step": request_id}
)
```

## FastMCP-Tx Decorator Features

### Tool-Level Configuration

```python
from mcp_tx import FastMCP-Tx, RetryPolicy

app = FastMCP-Tx(mcp_session)

@app.tool(
    retry_policy=RetryPolicy(max_attempts=3),
    timeout_ms=10000,
    idempotency_key_generator=lambda args: f"process-{args['id']}"
)
async def process_data(id: str, data: dict) -> dict:
    """Process with custom reliability settings."""
    return {"processed": True, "id": id}
```

### Automatic Features

When using FastMCP-Tx decorators:
- Input validation
- Type checking
- Thread-safe execution
- Deep copy protection
- Memory-bounded registry

## Implementation Details

### Protocol Negotiation

MCP-Tx features activate through capability negotiation:

```typescript
// Client announces MCP-Tx support
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "features": ["ack", "retry", "idempotency"]
      }
    }
  }
}
```

### Message Format

MCP-Tx extends standard MCP messages:

```typescript
// Request with MCP-Tx metadata
{
  "method": "tools/call",
  "params": {
    "name": "my_tool",
    "arguments": {},
    "_meta": {
      "rmcp": {
        "expect_ack": true,
        "request_id": "rmcp-123",
        "idempotency_key": "operation-456"
      }
    }
  }
}

// Response with guarantees
{
  "result": {},
  "_meta": {
    "rmcp": {
      "ack": true,
      "processed": true,
      "duplicate": false,
      "attempts": 2
    }
  }
}
```

## Best Practices

### 1. Choose Appropriate Retry Policies

```python
# Critical operations - aggressive retry
@app.tool(retry_policy=RetryPolicy(
    max_attempts=10,
    base_delay_ms=500
))
async def critical_operation(): ...

# User-facing operations - quick failure
@app.tool(retry_policy=RetryPolicy(
    max_attempts=2,
    base_delay_ms=1000
))
async def interactive_operation(): ...
```

### 2. Design Idempotent Operations

```python
# Good: Idempotent by design
@app.tool()
async def set_user_status(user_id: str, status: str):
    # Setting status is naturally idempotent
    await db.update_user(user_id, {"status": status})

# Better: Explicit idempotency
@app.tool(
    idempotency_key_generator=lambda args: f"status-{args['user_id']}-{args['status']}"
)
async def update_user_status(user_id: str, status: str):
    # MCP-Tx prevents duplicate updates
    await db.update_user(user_id, {"status": status})
```

### 3. Monitor Reliability Metrics

```python
# Track reliability in production
result = await app.call_tool("important_operation", data)

logger.info("Operation completed", extra={
    "tool": "important_operation",
    "attempts": result.rmcp_meta.attempts,
    "was_duplicate": result.rmcp_meta.duplicate,
    "latency_ms": result.rmcp_meta.latency_ms
})
```

## Comparison with Standard MCP

| Feature | Standard MCP | MCP-Tx |
|---------|-------------|------|
| Delivery Guarantee | Best effort | ACK required |
| Retry Logic | Client implements | Automatic with backoff |
| Duplicate Prevention | Client implements | Built-in deduplication |
| Error Visibility | Basic errors | Detailed failure reasons |
| Transaction Tracking | Manual | Automatic request IDs |

## See Also

- [Architecture Overview](architecture.md) - How MCP-Tx enhances MCP
- [Getting Started](getting-started.md) - Quick start guide
- [API Reference](api/mcp-tx-session.md) - Detailed API documentation

---

**Previous**: [Architecture](architecture.md) | **Next**: [Configuration Guide](configuration.md)