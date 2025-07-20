# Frequently Asked Questions

Common questions about MCP-Tx implementation and usage.

## General Questions

### What is MCP-Tx?

**MCP-Tx (Reliable Model Context Protocol)** is a reliability layer that wraps existing MCP sessions to provide delivery guarantees, automatic retry, request deduplication, and enhanced error handling. It's 100% backward compatible with standard MCP.

### Do I need to modify my MCP servers to use MCP-Tx?

**No.** MCP-Tx is designed for backward compatibility. It works with any existing MCP server:

- **MCP-Tx-aware servers**: Get full reliability features (ACK/NACK, server-side deduplication)
- **Standard MCP servers**: Automatic fallback with client-side reliability features

```python
# Works with any MCP server
rmcp_session = MCP-TxSession(your_mcp_session)
await rmcp_session.initialize()

print(f"MCP-Tx enabled: {rmcp_session.rmcp_enabled}")
# True = server supports MCP-Tx, False = fallback mode
```

### What's the performance impact of MCP-Tx?

**Minimal overhead** for most applications:

- **Latency**: < 1ms per request (metadata processing)
- **Memory**: ~10-100KB (request tracking, deduplication cache)
- **Network**: +200-500 bytes per request (MCP-Tx metadata)
- **CPU**: Negligible (async operations, efficient caching)

**Benchmark results** (vs standard MCP):
- Simple tool calls: +2-5% latency
- High concurrency: +1-3% latency  
- Large payloads: < 1% latency impact

### Can I use MCP-Tx with existing MCP libraries?

**Yes.** MCP-Tx wraps any object that implements the MCP session interface:

```python
# Works with any MCP client
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport
from mcp.client.sse import SseClientTransport
from rmcp import MCP-TxSession

# Standard MCP clients
mcp_session = ClientSession(StdioClientTransport(...))
# or
mcp_session = ClientSession(SseClientTransport(...))

# Wrap with MCP-Tx
rmcp_session = MCP-TxSession(mcp_session)
```

## Configuration Questions

### How do I customize retry behavior?

Use `RetryPolicy` to configure retry behavior per session or per call:

```python
from rmcp import MCP-TxSession, MCP-TxConfig, RetryPolicy

# Session-level retry policy
aggressive_retry = RetryPolicy(
    max_attempts=5,           # Try up to 5 times
    base_delay_ms=2000,       # Start with 2 second delay
    backoff_multiplier=2.0,   # Double delay each time: 2s, 4s, 8s, 16s
    jitter=True,              # Add randomness to prevent thundering herd
    retryable_errors=[        # Only retry these error types
        "CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED"
    ]
)

config = MCP-TxConfig(retry_policy=aggressive_retry)
rmcp_session = MCP-TxSession(mcp_session, config)

# Or per-call override
quick_retry = RetryPolicy(max_attempts=2, base_delay_ms=500)
result = await rmcp_session.call_tool(
    "fast_operation", 
    {},
    retry_policy=quick_retry
)
```

### What's the best idempotency key strategy?

**Create unique, deterministic keys** based on operation and parameters:

```python
import hashlib
import json
from datetime import datetime

def create_idempotency_key(operation: str, params: dict, user_id: str = None) -> str:
    """Create idempotency key for operation."""
    
    # Include operation type
    key_parts = [operation]
    
    # Add user context if available
    if user_id:
        key_parts.append(f"user-{user_id}")
    
    # Create deterministic hash from parameters
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    key_parts.append(params_hash)
    
    # Add date for natural expiration
    date_str = datetime.now().strftime("%Y%m%d")
    key_parts.append(date_str)
    
    return "-".join(key_parts)

# Example usage
idempotency_key = create_idempotency_key(
    "create_user",
    {"name": "Alice", "email": "alice@example.com"},
    user_id="admin_123"
)
# Result: "create_user-admin_123-a1b2c3d4-20240115"

result = await rmcp_session.call_tool(
    "user_creator",
    {"name": "Alice", "email": "alice@example.com"},
    idempotency_key=idempotency_key
)
```

### How do I configure timeouts for different operations?

**Set defaults in config, override per operation**:

```python
# Default timeout configuration
config = MCP-TxConfig(
    default_timeout_ms=10000,  # 10 seconds for most operations
)

rmcp_session = MCP-TxSession(mcp_session, config)

# Quick operations - shorter timeout
result = await rmcp_session.call_tool(
    "cache_lookup",
    {"key": "user_123"},
    timeout_ms=2000  # 2 seconds
)

# Slow operations - longer timeout  
result = await rmcp_session.call_tool(
    "large_file_processor",
    {"file_path": "/data/huge_file.csv"},
    timeout_ms=300000  # 5 minutes
)

# Critical operations - very long timeout
result = await rmcp_session.call_tool(
    "database_backup",
    {"target": "s3://backup-bucket"},
    timeout_ms=600000  # 10 minutes (max allowed)
)
```

## Error Handling Questions

### How do I handle different types of errors?

**Use specific exception types** for targeted error handling:

```python
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError, MCP-TxError

async def robust_operation():
    try:
        result = await rmcp_session.call_tool("external_api", {"endpoint": "/data"})
        
        if result.ack:
            return result.result
        else:
            # Tool executed but returned error
            raise RuntimeError(f"Tool failed: {result.rmcp_meta.error_message}")
            
    except MCP-TxTimeoutError as e:
        # Handle timeout - maybe retry with longer timeout
        print(f"Operation timed out after {e.details['timeout_ms']}ms")
        return await rmcp_session.call_tool(
            "external_api", 
            {"endpoint": "/data"},
            timeout_ms=60000  # Longer timeout
        )
        
    except MCP-TxNetworkError as e:
        # Handle network issues - maybe wait and retry
        print(f"Network error: {e.message}")
        await asyncio.sleep(5)
        return await rmcp_session.call_tool("external_api", {"endpoint": "/data"})
        
    except MCP-TxError as e:
        # Handle other MCP-Tx errors
        if e.retryable:
            print(f"Retryable error: {e.message}")
            # MCP-Tx already retried, so log and handle gracefully
        else:
            print(f"Permanent error: {e.message}")
            # Don't retry, handle as final failure
        
        raise e
```

### What does `result.ack` vs `result.processed` mean?

**Different levels of guarantees**:

```python
result = await rmcp_session.call_tool("test_tool", {})

# result.ack = True means:
#   - Request was received by server
#   - Server attempted to process it
#   - Server sent acknowledgment back
#   - Network delivery was successful

# result.processed = True means:
#   - Tool was actually executed
#   - Tool completed (successfully or with error)
#   - Result is available in result.result

# Possible combinations:
if result.ack and result.processed:
    # Best case: confirmed execution
    print(f"Success: {result.result}")
    
elif result.ack and not result.processed:
    # Server received but couldn't process
    print(f"Server error: {result.rmcp_meta.error_message}")
    
elif not result.ack:
    # Network/infrastructure failure
    print(f"Delivery failed: {result.rmcp_meta.error_message}")
    # This case triggers automatic retry
```

### How do I debug MCP-Tx issues?

**Enable debug logging** to see MCP-Tx internals:

```python
import logging

# Enable MCP-Tx debug logging
logging.basicConfig(level=logging.DEBUG)
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# Now MCP-Tx will log:
# - Request ID generation
# - Retry attempts and delays
# - Cache hits/misses
# - Server capability negotiation
# - Error details

async with MCP-TxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    
    # Debug information in logs
    result = await rmcp.call_tool("test", {})
    
    # Also check active requests
    print(f"Active requests: {len(rmcp.active_requests)}")
    for req_id, tracker in rmcp.active_requests.items():
        print(f"  {req_id}: {tracker.status} ({tracker.attempts} attempts)")
```

## Advanced Usage Questions

### Can I use MCP-Tx with multiple MCP servers?

**Yes, create separate MCP-Tx sessions** for each server:

```python
# Multiple servers with different configurations
from rmcp import MCP-TxSession, MCP-TxConfig, RetryPolicy

# Fast, reliable server - minimal retry
fast_config = MCP-TxConfig(
    retry_policy=RetryPolicy(max_attempts=2, base_delay_ms=500),
    default_timeout_ms=5000
)
fast_rmcp = MCP-TxSession(fast_mcp_session, fast_config)

# Slow, unreliable server - aggressive retry
slow_config = MCP-TxConfig(
    retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=2000),
    default_timeout_ms=30000
)
slow_rmcp = MCP-TxSession(slow_mcp_session, slow_config)

# Use appropriate session for each operation
fast_result = await fast_rmcp.call_tool("cache_lookup", {"key": "data"})
slow_result = await slow_rmcp.call_tool("ml_inference", {"model": "large"})
```

### How do I implement circuit breaker pattern?

**Manual circuit breaker** (automatic version coming in Session 2):

```python
import time
from collections import defaultdict

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = defaultdict(int)
        self.last_failure = defaultdict(float)
    
    def is_open(self, tool_name: str) -> bool:
        """Check if circuit is open for this tool."""
        if self.failures[tool_name] >= self.failure_threshold:
            # Check if timeout has elapsed
            if time.time() - self.last_failure[tool_name] > self.timeout:
                # Reset circuit breaker
                self.failures[tool_name] = 0
                return False
            return True
        return False
    
    def record_success(self, tool_name: str):
        """Record successful call."""
        self.failures[tool_name] = 0
    
    def record_failure(self, tool_name: str):
        """Record failed call."""
        self.failures[tool_name] += 1
        self.last_failure[tool_name] = time.time()

# Usage with MCP-Tx
circuit_breaker = CircuitBreaker()

async def call_with_circuit_breaker(tool_name: str, arguments: dict):
    if circuit_breaker.is_open(tool_name):
        raise RuntimeError(f"Circuit breaker open for {tool_name}")
    
    try:
        result = await rmcp_session.call_tool(tool_name, arguments)
        
        if result.ack:
            circuit_breaker.record_success(tool_name)
            return result.result
        else:
            circuit_breaker.record_failure(tool_name)
            raise RuntimeError(f"Tool failed: {result.rmcp_meta.error_message}")
            
    except Exception as e:
        circuit_breaker.record_failure(tool_name)
        raise e
```

### How do I implement custom retry logic?

**Override retry behavior** with custom policies:

```python
from rmcp import RetryPolicy

# Custom retry for different error types
class SmartRetryPolicy(RetryPolicy):
    def __init__(self):
        super().__init__(
            max_attempts=3,
            base_delay_ms=1000,
            backoff_multiplier=1.5,
            jitter=True
        )
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Custom retry logic."""
        
        # Never retry validation errors
        if "validation" in str(error).lower():
            return False
        
        # Aggressive retry for rate limits
        if "rate limit" in str(error).lower():
            return attempt < 10  # Up to 10 attempts
        
        # Quick give up for auth errors
        if "unauthorized" in str(error).lower():
            return False
        
        # Default behavior for other errors
        return attempt < self.max_attempts
    
    def get_delay(self, attempt: int, error: Exception) -> int:
        """Custom delay calculation."""
        
        # Longer delays for rate limits
        if "rate limit" in str(error).lower():
            return min(30000, 5000 * (2 ** attempt))  # 5s, 10s, 20s, 30s max
        
        # Shorter delays for network errors
        if "network" in str(error).lower():
            return min(5000, 500 * (1.5 ** attempt))  # 500ms, 750ms, 1125ms, etc.
        
        # Default exponential backoff
        return super().get_delay(attempt, error)

# Use custom retry policy
smart_retry = SmartRetryPolicy()
result = await rmcp_session.call_tool(
    "api_endpoint",
    {"data": "payload"},
    retry_policy=smart_retry
)
```

## Integration Questions

### How do I integrate MCP-Tx with FastAPI?

**Use dependency injection** for MCP-Tx sessions:

```python
from fastapi import FastAPI, Depends, HTTPException
from rmcp import MCP-TxSession
import asyncio

app = FastAPI()

# Global MCP-Tx session (or use dependency injection)
_rmcp_session = None

async def get_rmcp_session() -> MCP-TxSession:
    """FastAPI dependency for MCP-Tx session."""
    global _rmcp_session
    if _rmcp_session is None:
        # Initialize MCP-Tx session
        mcp_session = await setup_mcp_session()
        _rmcp_session = MCP-TxSession(mcp_session)
        await _rmcp_session.initialize()
    
    return _rmcp_session

@app.post("/process-file")
async def process_file(
    file_path: str,
    rmcp: MCP-TxSession = Depends(get_rmcp_session)
):
    """Process file using MCP-Tx."""
    try:
        result = await rmcp.call_tool(
            "file_processor",
            {"path": file_path},
            idempotency_key=f"process-{file_path.replace('/', '_')}"
        )
        
        if result.ack:
            return {
                "success": True,
                "result": result.result,
                "attempts": result.attempts
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {result.rmcp_meta.error_message}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown():
    """Clean up MCP-Tx session on shutdown."""
    global _rmcp_session
    if _rmcp_session:
        await _rmcp_session.close()
```

### How do I use MCP-Tx with asyncio.gather()?

**MCP-Tx works seamlessly** with asyncio concurrency:

```python
import asyncio

async def concurrent_operations():
    """Run multiple MCP-Tx operations concurrently."""
    
    # Create list of concurrent operations
    operations = [
        rmcp_session.call_tool("processor_1", {"data": f"batch_{i}"})
        for i in range(10)
    ]
    
    # Execute all operations concurrently
    results = await asyncio.gather(*operations, return_exceptions=True)
    
    # Process results
    successful_results = []
    failed_operations = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_operations.append((i, str(result)))
        elif result.ack:
            successful_results.append(result.result)
        else:
            failed_operations.append((i, result.rmcp_meta.error_message))
    
    print(f"Successful: {len(successful_results)}")
    print(f"Failed: {len(failed_operations)}")
    
    return successful_results, failed_operations
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'rmcp'"

```bash
# Install MCP-Tx
uv add mcp_tx
# or
pip install mcp_tx
```

### "MCP-TxResult object has no attribute 'content'"

```python
# ❌ Wrong: Accessing MCP result directly
result = await rmcp_session.call_tool("test", {})
print(result.content)  # AttributeError

# ✅ Correct: Access through result.result
result = await rmcp_session.call_tool("test", {})
if result.ack:
    print(result.result)  # This contains the actual MCP result
```

### "MCP-Tx session not initialized"

```python
# ❌ Wrong: Forgot to initialize
rmcp_session = MCP-TxSession(mcp_session)
result = await rmcp_session.call_tool("test", {})  # Error

# ✅ Correct: Always initialize first
rmcp_session = MCP-TxSession(mcp_session)
await rmcp_session.initialize()  # Required step
result = await rmcp_session.call_tool("test", {})
```

### High memory usage

```python
# Configure cache limits to prevent memory leaks
config = MCP-TxConfig(
    deduplication_window_ms=300000,  # 5 minutes instead of default 10
    max_concurrent_requests=5,       # Limit concurrent requests
)

rmcp_session = MCP-TxSession(mcp_session, config)
```

---

**Previous**: [Migration Guide](migration.md) | **Next**: [Troubleshooting](troubleshooting.md)