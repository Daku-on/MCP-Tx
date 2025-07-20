# MCP-Tx Performance Guide

This guide covers performance optimization strategies for MCP-Tx in production environments.

## Performance Overview

MCP-Tx adds reliability features with minimal overhead:
- **Latency overhead**: ~1-5ms per request (ACK/NACK processing)
- **Memory overhead**: ~1KB per active request (deduplication tracking)
- **Network overhead**: ~200 bytes per request (MCP-Tx metadata)

## Quick Performance Wins

### 1. Optimize Timeouts

```python
from mcp_tx import MCPTxConfig, FastMCP-Tx

# Fast-fail configuration for interactive applications
config = MCPTxConfig(
    default_timeout_ms=5000,  # 5 seconds max wait
    retry_policy=RetryPolicy(
        max_attempts=2,  # Quick retry only
        base_delay_ms=500
    )
)

app = FastMCP-Tx(mcp_session, config)
```

### 2. Batch Operations

```python
# Instead of sequential calls
results = []
for item in items:
    result = await app.call_tool("process", {"item": item})
    results.append(result)

# Use concurrent execution
import asyncio

async def process_item(item):
    return await app.call_tool("process", {"item": item})

# Process in parallel (respects max_concurrent_requests)
results = await asyncio.gather(*[
    process_item(item) for item in items
])
```

### 3. Connection Pooling

```python
# Reuse sessions for multiple operations
async with FastMCP-Tx(mcp_session) as app:
    # All operations share the same connection pool
    for i in range(1000):
        await app.call_tool("operation", {"id": i})
```

## Concurrency Optimization

### Configure Concurrent Limits

```python
# High-concurrency configuration
config = MCPTxConfig(
    max_concurrent_requests=50,  # Increase parallel operations
    default_timeout_ms=10000
)

# Per-tool concurrency control
@app.tool()
async def batch_processor(items: list) -> dict:
    """Process items with controlled concurrency."""
    semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
    
    async def process_one(item):
        async with semaphore:
            return await expensive_operation(item)
    
    results = await asyncio.gather(*[
        process_one(item) for item in items
    ])
    return {"processed": len(results)}
```

### Async Best Practices

```python
# Good: True async operations
@app.tool()
async def efficient_io(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return {"data": await response.json()}

# Bad: Blocking operations in async
@app.tool()
async def inefficient_io(url: str) -> dict:
    # This blocks the event loop!
    response = requests.get(url)  # ❌ Synchronous
    return {"data": response.json()}
```

## Memory Optimization

### Deduplication Window Tuning

```python
# Short-lived operations: smaller window
config = MCPTxConfig(
    deduplication_window_ms=60000  # 1 minute
)

# Long-running workflows: larger window
config = MCPTxConfig(
    deduplication_window_ms=3600000  # 1 hour
)

# Memory usage: ~1KB per unique request in window
# 1 hour window + 1000 req/min = ~60MB memory
```

### Tool Registry Management

```python
# Limit tool registry size
app = FastMCP-Tx(
    mcp_session,
    max_tools=100  # Prevent unbounded growth
)

# Dynamic tool registration/cleanup
class ManagedApp:
    def __init__(self, mcp_session):
        self.app = FastMCP-Tx(mcp_session)
        self.tool_usage = {}
    
    def register_tool_with_ttl(self, tool_func, ttl_seconds=3600):
        """Register tool with automatic cleanup."""
        self.app.tool()(tool_func)
        self.tool_usage[tool_func.__name__] = time.time()
        
        # Schedule cleanup
        asyncio.create_task(self._cleanup_tool(tool_func.__name__, ttl_seconds))
```

## Network Optimization

### Message Compression

```python
# Enable compression for large payloads
config = MCPTxConfig(
    enable_compression=True,  # Gzip for messages > 1KB
    compression_threshold_bytes=1024
)

# Efficient for large data transfers
@app.tool()
async def transfer_large_data(data: dict) -> dict:
    # Compression happens automatically
    return {"processed": len(json.dumps(data))}
```

### Retry Strategy Optimization

```python
from mcp_tx import RetryPolicy

# Network-optimized retry
network_retry = RetryPolicy(
    max_attempts=3,
    base_delay_ms=100,    # Start fast
    max_delay_ms=5000,    # Cap at 5 seconds
    backoff_multiplier=3.0,  # Aggressive backoff
    jitter=True  # Prevent thundering herd
)

# CPU-bound operation retry
cpu_retry = RetryPolicy(
    max_attempts=2,  # Don't retry expensive operations
    base_delay_ms=5000  # Give system time to recover
)
```

## Monitoring and Profiling

### Performance Metrics

```python
import time
from contextlib import asynccontextmanager

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'total_calls': 0,
            'total_retries': 0,
            'total_time_ms': 0,
            'errors': 0
        }
    
    @asynccontextmanager
    async def track_call(self, tool_name: str):
        start = time.time()
        try:
            yield
            self.metrics['total_calls'] += 1
        except Exception as e:
            self.metrics['errors'] += 1
            raise
        finally:
            elapsed = (time.time() - start) * 1000
            self.metrics['total_time_ms'] += elapsed
            
            # Log slow operations
            if elapsed > 1000:  # 1 second
                logger.warning(f"Slow operation: {tool_name} took {elapsed:.0f}ms")

# Usage
monitor = PerformanceMonitor()

@app.tool()
async def monitored_operation(data: dict) -> dict:
    async with monitor.track_call("monitored_operation"):
        return await process_data(data)
```

### Resource Usage Tracking

```python
import psutil
import asyncio

class ResourceMonitor:
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.baseline_memory = psutil.Process().memory_info().rss
    
    async def monitor_loop(self):
        """Background monitoring task."""
        while True:
            process = psutil.Process()
            current_memory = process.memory_info().rss
            memory_delta = (current_memory - self.baseline_memory) / 1024 / 1024  # MB
            
            logger.info(f"MCP-Tx Stats: "
                       f"Tools: {len(self.app.list_tools())}, "
                       f"Memory Delta: {memory_delta:.1f}MB, "
                       f"CPU: {process.cpu_percent()}%")
            
            await asyncio.sleep(60)  # Check every minute
```

## Production Optimizations

### Load Balancing

```python
class LoadBalancedMCP-Tx:
    """Distribute load across multiple MCP sessions."""
    
    def __init__(self, mcp_sessions: list):
        self.apps = [FastMCP-Tx(session) for session in mcp_sessions]
        self.current = 0
    
    async def call_tool(self, name: str, arguments: dict) -> MCP-TxResult:
        # Round-robin selection
        app = self.apps[self.current]
        self.current = (self.current + 1) % len(self.apps)
        
        return await app.call_tool(name, arguments)
```

### Caching Layer

```python
from functools import lru_cache
import hashlib

class CachedMCP-Tx:
    """Add caching to idempotent operations."""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def call_tool_cached(self, name: str, arguments: dict) -> MCP-TxResult:
        # Generate cache key
        cache_key = hashlib.md5(
            f"{name}:{json.dumps(arguments, sort_keys=True)}".encode()
        ).hexdigest()
        
        # Check cache
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        # Execute and cache
        result = await self.app.call_tool(name, arguments)
        self.cache[cache_key] = (result, time.time())
        
        return result
```

### Connection Warmup

```python
async def warmup_rmcp(app: FastMCP-Tx):
    """Pre-warm connections for better latency."""
    # Initialize connection pool
    await app.initialize()
    
    # Execute dummy operations to establish connections
    warmup_tasks = []
    for i in range(5):
        task = app.call_tool("ping", {}, timeout_ms=1000)
        warmup_tasks.append(task)
    
    # Wait for warmup to complete
    await asyncio.gather(*warmup_tasks, return_exceptions=True)
    
    logger.info("MCP-Tx connection pool warmed up")
```

## Performance Benchmarks

### Baseline Performance

```python
async def benchmark_rmcp(app: FastMCP-Tx, iterations: int = 1000):
    """Measure MCP-Tx performance characteristics."""
    
    # Sequential performance
    start = time.time()
    for i in range(iterations):
        await app.call_tool("echo", {"value": i})
    sequential_time = time.time() - start
    
    # Concurrent performance
    start = time.time()
    tasks = [
        app.call_tool("echo", {"value": i})
        for i in range(iterations)
    ]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start
    
    print(f"Sequential: {iterations / sequential_time:.0f} ops/sec")
    print(f"Concurrent: {iterations / concurrent_time:.0f} ops/sec")
    print(f"Speedup: {sequential_time / concurrent_time:.1f}x")
```

### Expected Performance

| Operation Type | Latency | Throughput |
|---------------|---------|------------|
| Simple tool call | 5-10ms | 100-200 ops/sec/connection |
| With retry (1 attempt) | 10-20ms | 50-100 ops/sec/connection |
| With retry (3 attempts) | 30-100ms | 10-30 ops/sec/connection |
| Concurrent (10 parallel) | 5-10ms | 1000-2000 ops/sec total |

## Optimization Checklist

- [ ] **Timeouts**: Set appropriate timeouts for your use case
- [ ] **Concurrency**: Configure max_concurrent_requests
- [ ] **Retry Policy**: Balance reliability vs performance
- [ ] **Connection Pooling**: Reuse sessions
- [ ] **Async Operations**: Ensure all I/O is truly async
- [ ] **Batching**: Group related operations
- [ ] **Caching**: Cache idempotent results
- [ ] **Monitoring**: Track performance metrics
- [ ] **Resource Limits**: Set memory bounds
- [ ] **Compression**: Enable for large payloads

## See Also

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Architecture Overview](architecture.md) - Understanding MCP-Tx internals
- [Troubleshooting](troubleshooting.md) - Common performance issues

---

**Previous**: [Configuration Guide](configuration.md) | **Next**: [API Reference](api/mcp-tx-session.md)