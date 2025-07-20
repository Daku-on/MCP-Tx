# Troubleshooting Guide

Common issues and solutions when using RMCP.

## Installation Issues

### "No module named 'rmcp'"

**Problem**: Import error when trying to use RMCP
```python
ModuleNotFoundError: No module named 'rmcp'
```

**Solutions**:
```bash
# Install with uv (recommended)
uv add rmcp

# Or install with pip
pip install rmcp

# Verify installation
python -c "import rmcp; print(rmcp.__version__)"
```

### Dependency Conflicts

**Problem**: Package version conflicts during installation

**Solutions**:
```bash
# Check for conflicts
uv tree

# Update dependencies
uv sync --upgrade

# Use fresh virtual environment
uv venv --clear
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
uv add rmcp
```

## Session Initialization Issues

### "RMCP session not initialized"

**Problem**: Calling `call_tool()` without initializing session
```python
rmcp_session = RMCPSession(mcp_session)
result = await rmcp_session.call_tool("test", {})  # Error!
```

**Solution**: Always call `initialize()` first
```python
rmcp_session = RMCPSession(mcp_session)
await rmcp_session.initialize()  # Required!
result = await rmcp_session.call_tool("test", {})
```

### Server Capability Negotiation Fails

**Problem**: Server doesn't respond to RMCP capabilities

**Symptoms**:
- `rmcp_session.rmcp_enabled` is `False`
- All operations fall back to standard MCP

**Solutions**:
```python
# Check server capabilities after initialization
await rmcp_session.initialize()
if not rmcp_session.rmcp_enabled:
    print("⚠️ Server doesn't support RMCP - using fallback mode")
    # This is normal and expected for many servers

# Force debug logging to see negotiation
import logging
logging.getLogger("rmcp").setLevel(logging.DEBUG)
```

### Async Context Manager Issues

**Problem**: Session not properly closed, resource leaks

**Bad Pattern**:
```python
rmcp = RMCPSession(mcp_session)
await rmcp.initialize()
# ... use rmcp
# Session never closed - resource leak!
```

**Good Patterns**:
```python
# ✅ Best: Use async context manager
async with RMCPSession(mcp_session) as rmcp:
    await rmcp.initialize()
    # ... use rmcp
    # Automatically closed

# ✅ Acceptable: Manual cleanup
rmcp = RMCPSession(mcp_session)
try:
    await rmcp.initialize()
    # ... use rmcp
finally:
    await rmcp.close()
```

## Result Handling Issues

### "RMCPResult object has no attribute 'content'"

**Problem**: Trying to access MCP result directly
```python
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})
content = result.content  # AttributeError!
```

**Solution**: Access result through `.result` attribute
```python
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

if result.ack:
    content = result.result.get("content", "")  # ✅ Correct
    print(f"File content: {content}")
else:
    print(f"Failed: {result.rmcp_meta.error_message}")
```

### Confusing ACK vs Processed States

**Problem**: Misunderstanding `result.ack` vs `result.processed`

**Explanation**:
```python
result = await rmcp_session.call_tool("test_tool", {})

# result.ack = True means:
#   - Request was delivered to server
#   - Server attempted to process it
#   - Server sent acknowledgment back

# result.processed = True means:
#   - Tool was actually executed
#   - Tool completed (successfully or with error)
#   - Result is available in result.result

# Check both for different scenarios
if result.ack and result.processed:
    print("✅ Tool executed successfully")
    print(f"Result: {result.result}")
elif result.ack and not result.processed:
    print("⚠️ Server received request but couldn't execute tool")
    print(f"Reason: {result.rmcp_meta.error_message}")
else:
    print("❌ Request failed to reach server or get acknowledgment")
    print(f"Error: {result.rmcp_meta.error_message}")
```

## Configuration Issues

### Timeout Errors with Large Operations

**Problem**: Operations timing out on large data
```python
# Times out after default 10 seconds
result = await rmcp_session.call_tool("process_large_file", {"path": "/huge.csv"})
# RMCPTimeoutError!
```

**Solutions**:
```python
# Solution 1: Per-call timeout override
result = await rmcp_session.call_tool(
    "process_large_file",
    {"path": "/huge.csv"},
    timeout_ms=300000  # 5 minutes
)

# Solution 2: Configure session defaults
config = RMCPConfig(default_timeout_ms=60000)  # 1 minute default
rmcp_session = RMCPSession(mcp_session, config)

# Solution 3: Environment-specific configuration
def get_timeout_for_environment():
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return 30000  # 30 seconds
    elif env == "staging":
        return 15000  # 15 seconds
    else:
        return 5000   # 5 seconds (fast dev cycles)

config = RMCPConfig(default_timeout_ms=get_timeout_for_environment())
```

### Memory Usage Growing Over Time

**Problem**: Memory usage increases with long-running sessions

**Causes**:
- Large deduplication cache
- Many concurrent requests
- Request tracking not cleaned up

**Solutions**:
```python
# Reduce cache window
config = RMCPConfig(
    deduplication_window_ms=300000,  # 5 minutes instead of default 10
    max_concurrent_requests=5,       # Limit concurrent requests
)

# Monitor memory usage
import psutil
import os

def check_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.1f} MB")

# Check periodically
check_memory()
result = await rmcp_session.call_tool("test", {})
check_memory()
```

### Retry Policy Not Working as Expected

**Problem**: Retries not happening or happening too aggressively

**Common Issues**:
```python
# ❌ Problem: Retry policy with no retryable errors
bad_policy = RetryPolicy(
    max_attempts=5,
    retryable_errors=[]  # Empty list - nothing will retry!
)

# ✅ Solution: Include appropriate error types
good_policy = RetryPolicy(
    max_attempts=5,
    retryable_errors=["CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR"]
)

# ❌ Problem: Too aggressive retry
aggressive_policy = RetryPolicy(
    max_attempts=10,        # Too many attempts
    base_delay_ms=100,      # Too short delay
    backoff_multiplier=1.0  # No backoff!
)

# ✅ Solution: Reasonable retry policy
reasonable_policy = RetryPolicy(
    max_attempts=3,         # Reasonable attempts
    base_delay_ms=1000,     # 1 second base delay
    backoff_multiplier=2.0, # Exponential backoff
    jitter=True            # Prevent thundering herd
)
```

## Error Handling Issues

### Generic Exception Handling Hiding Issues

**Problem**: Catching all exceptions loses important error context
```python
# ❌ Bad: Generic exception handling
try:
    result = await rmcp_session.call_tool("api_call", {})
except Exception as e:
    print(f"Something went wrong: {e}")
    return None  # Lost all error context!
```

**Solution**: Handle specific RMCP exceptions
```python
# ✅ Good: Specific exception handling
from rmcp.types import RMCPTimeoutError, RMCPNetworkError

try:
    result = await rmcp_session.call_tool("api_call", {})
    
except RMCPTimeoutError as e:
    print(f"Operation timed out after {e.details['timeout_ms']}ms")
    # Maybe retry with longer timeout or different approach
    
except RMCPNetworkError as e:
    print(f"Network error: {e.message}")
    # Maybe check network connectivity or retry later
    
except ValueError as e:
    print(f"Invalid input parameters: {e}")
    # Fix the input and try again
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Log for debugging, but still handle gracefully
```

### Error Messages Not Descriptive Enough

**Problem**: Error messages don't provide enough context for debugging

**Solutions**:
```python
# Enable debug logging for more details
import logging
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# Create custom error handlers with more context
async def call_tool_with_context(tool_name: str, arguments: dict):
    try:
        return await rmcp_session.call_tool(tool_name, arguments)
    except Exception as e:
        print(f"Tool call failed:")
        print(f"  Tool: {tool_name}")
        print(f"  Arguments: {arguments}")
        print(f"  Error: {e}")
        print(f"  RMCP enabled: {rmcp_session.rmcp_enabled}")
        print(f"  Active requests: {len(rmcp_session.active_requests)}")
        raise
```

## Performance Issues

### Slow Tool Calls

**Problem**: RMCP operations seem slower than expected

**Debugging Steps**:
```python
import time

async def benchmark_call(tool_name: str, arguments: dict):
    start_time = time.time()
    
    result = await rmcp_session.call_tool(tool_name, arguments)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    
    print(f"Tool: {tool_name}")
    print(f"Duration: {duration_ms:.1f}ms") 
    print(f"Attempts: {result.attempts}")
    print(f"RMCP enabled: {rmcp_session.rmcp_enabled}")
    
    return result

# Compare with direct MCP call
start_time = time.time()
direct_result = await mcp_session.call_tool(tool_name, arguments)
direct_duration = (time.time() - start_time) * 1000

print(f"Direct MCP: {direct_duration:.1f}ms")
print(f"RMCP overhead: {duration_ms - direct_duration:.1f}ms")
```

**Common Causes & Solutions**:
```python
# High concurrency limit causing resource contention
config = RMCPConfig(max_concurrent_requests=5)  # Reduce from default 10

# Unnecessary retry attempts
quick_policy = RetryPolicy(max_attempts=1)  # No retries for simple operations
result = await rmcp_session.call_tool("fast_op", {}, retry_policy=quick_policy)

# Large deduplication cache causing memory pressure
config = RMCPConfig(deduplication_window_ms=60000)  # 1 minute instead of 10
```

### High Retry Rates

**Problem**: Too many operations requiring retries

**Investigation**:
```python
# Track retry statistics
retry_stats = {"total": 0, "retried": 0, "max_attempts": 0}

async def track_retries(tool_name: str, arguments: dict):
    result = await rmcp_session.call_tool(tool_name, arguments)
    
    retry_stats["total"] += 1
    if result.attempts > 1:
        retry_stats["retried"] += 1
        retry_stats["max_attempts"] = max(retry_stats["max_attempts"], result.attempts)
    
    return result

# After running operations
retry_rate = retry_stats["retried"] / retry_stats["total"] * 100
print(f"Retry rate: {retry_rate:.1f}%")
print(f"Max attempts seen: {retry_stats['max_attempts']}")

# If retry rate > 20%, investigate:
# 1. Network stability
# 2. Server reliability  
# 3. Timeout configuration
# 4. Resource contention
```

## Debugging Tools

### Enable Debug Logging

```python
import logging

# Configure logging for RMCP internals
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Specific loggers
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# Now RMCP will log:
# - Request ID generation
# - Retry attempts and delays  
# - Cache hits/misses
# - Server capability negotiation
# - Error details and context
```

### Session Introspection

```python
async def debug_session_state(rmcp_session: RMCPSession):
    print("=== RMCP Session Debug Info ===")
    print(f"RMCP enabled: {rmcp_session.rmcp_enabled}")
    print(f"Active requests: {len(rmcp_session.active_requests)}")
    
    for req_id, tracker in rmcp_session.active_requests.items():
        print(f"  {req_id}: {tracker.status} ({tracker.attempts} attempts)")
    
    # Memory usage
    import sys
    print(f"Session object size: {sys.getsizeof(rmcp_session)} bytes")
    
    # Configuration
    config = rmcp_session.config
    print(f"Default timeout: {config.default_timeout_ms}ms")
    print(f"Max concurrent: {config.max_concurrent_requests}")
    print(f"Dedup window: {config.deduplication_window_ms}ms")

# Call periodically during debugging
await debug_session_state(rmcp_session)
```

### Network Diagnostics

```python
import aiohttp
import asyncio

async def test_network_connectivity():
    """Test basic network connectivity."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/get", timeout=5) as response:
                if response.status == 200:
                    print("✅ Network connectivity OK")
                else:
                    print(f"⚠️ Network issue: Status {response.status}")
    except asyncio.TimeoutError:
        print("❌ Network timeout")
    except Exception as e:
        print(f"❌ Network error: {e}")

async def test_mcp_connectivity(mcp_session):
    """Test direct MCP connectivity."""
    try:
        # Try a simple MCP operation
        result = await mcp_session.call_tool("echo", {"message": "test"})
        print("✅ MCP connectivity OK")
    except Exception as e:
        print(f"❌ MCP connectivity issue: {e}")

# Run diagnostics
await test_network_connectivity()
await test_mcp_connectivity(mcp_session)
```

## Getting Help

### Information to Include in Bug Reports

When reporting issues, include:

1. **Environment Information**:
```python
import sys
import rmcp
print(f"Python version: {sys.version}")
print(f"RMCP version: {rmcp.__version__}")
print(f"Platform: {sys.platform}")
```

2. **Configuration**:
```python
print(f"RMCP config: {rmcp_session.config}")
print(f"RMCP enabled: {rmcp_session.rmcp_enabled}")
```

3. **Error Details**:
```python
# Full exception traceback
# Specific error message
# Steps to reproduce
# Expected vs actual behavior
```

4. **Debug Logs**:
```python
# Enable debug logging and include relevant log output
logging.getLogger("rmcp").setLevel(logging.DEBUG)
```

### Community Resources

- **GitHub Issues**: [reliable-MCP-draft/issues](https://github.com/takako/reliable-MCP-draft/issues)
- **Documentation**: This docs directory
- **Examples**: `docs/examples/` directory

---

**Previous**: [FAQ](faq.md) | **Next**: [Performance Guide](performance.md)