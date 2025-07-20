# MCP-Tx Architecture Overview

Understanding how MCP-Tx enhances MCP with reliability guarantees.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│                 │    │                      │    │                 │
│   Your Client   │    │    MCP-Tx Session      │    │   MCP Server    │
│   Application   │    │   (Reliability       │    │   (Existing)    │
│                 │    │    Wrapper)          │    │                 │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
         │                        │                          │
         │ call_tool()            │ Enhanced MCP             │ Standard MCP  
         ├─────────────────────▶  │ with _meta.rmcp         ├──────────────▶
         │                        │                          │
         │ MCP-TxResult             │ Standard MCP             │ Tool Result
         ◀─────────────────────── │ Response                 ◀──────────────┤
         │                        │                          │
```

## Core Components

### 1. MCP-TxSession (Wrapper)

The main interface that wraps any existing MCP session:

```python
class MCP-TxSession:
    def __init__(self, mcp_session: BaseSession, config: MCP-TxConfig = None):
        self.mcp_session = mcp_session  # Your existing MCP session
        self.config = config or MCP-TxConfig()
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
      "rmcp": {
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
    "_meta": {"rmcp": {"expect_ack": True, ...}},
    ...
}

# Server processes and responds with ACK
response = {
    "result": {...},
    "_meta": {
        "rmcp": {
            "ack": True,           # Explicit acknowledgment
            "processed": True,     # Tool was executed
            "request_id": "...",   # Correlation
        }
    }
}

# Client validates ACK and returns MCP-TxResult
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
class MCP-TxSession:
    def __init__(self):
        # LRU cache with TTL for memory safety
        self._deduplication_cache: dict[str, tuple[MCP-TxResult, datetime]] = {}
    
    def _get_cached_result(self, idempotency_key: str) -> MCP-TxResult | None:
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
class MCP-TxSession:
    def __init__(self, config: MCP-TxConfig):
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
kwargs["capabilities"]["experimental"]["rmcp"] = {
    "version": "0.1.0",
    "features": ["ack", "retry", "idempotency", "transactions"]
}
```

### Server Response
```python
# Server responds with supported MCP-Tx features
server_capabilities = {
    "experimental": {
        "rmcp": {
            "version": "0.1.0", 
            "features": ["ack", "retry"]  # Subset of client features
        }
    }
}
```

### Fallback Behavior
```python
if not self._rmcp_enabled:
    # Transparent fallback to standard MCP
    return await self._execute_standard_mcp_call(name, arguments, timeout_ms)
else:
    # Enhanced MCP with MCP-Tx metadata
    return await self._execute_rmcp_call(name, arguments, rmcp_meta, timeout_ms)
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
class MCP-TxError(Exception):
    def __init__(self, message: str, error_code: str, retryable: bool):
        self.retryable = retryable  # Determines retry behavior

# Specific error types
MCP-TxTimeoutError(retryable=True)    # Retry on timeout
MCP-TxNetworkError(retryable=True)    # Retry on network issues  
MCP-TxSequenceError(retryable=False)  # Don't retry on sequence errors
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
        r"password[=:]\\s*\\S+", r"token[=:]\\s*\\S+", 
        r"key[=:]\\s*\\S+", r"/Users/[^/\\s]+", r"/home/[^/\\s]+"
    ]
    # ... sanitization logic
```

### Capability Validation
- Server capabilities are validated during negotiation
- Unknown/unsafe features are ignored
- Graceful degradation for unsupported features

## Next Steps

- [**Getting Started**](getting-started.md) - Quick start with configuration examples
- [**API Reference**](api/rmcp-session.md) - Detailed method documentation
- [**Examples**](examples/basic.md) - Practical usage patterns

---

**Previous**: [Getting Started](getting-started.md) | **Next**: [API Reference](api/rmcp-session.md)