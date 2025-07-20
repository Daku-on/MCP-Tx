# MCP-Tx Configuration Guide

This guide covers all configuration options available in MCP-Tx, from basic settings to advanced tuning.

## Quick Start Configuration

### Basic Setup

```python
from mcp_tx import MCPTxConfig, MCPTxSession

# Default configuration (recommended for most use cases)
config = MCPTxConfig()
session = MCPTxSession(mcp_session, config)
```

### Common Customizations

```python
from mcp_tx import MCPTxConfig, RetryPolicy

# Production-ready configuration
config = MCPTxConfig(
    # Timeouts
    default_timeout_ms=30000,        # 30 seconds
    
    # Concurrency
    max_concurrent_requests=10,      # Limit parallel operations
    
    # Deduplication
    deduplication_window_ms=300000,  # 5 minutes
    
    # Retry behavior
    retry_policy=RetryPolicy(
        max_attempts=3,
        base_delay_ms=1000,
        backoff_multiplier=2.0
    ),
    
    # Logging
    enable_request_logging=True,
    log_level="INFO"
)
```

## Configuration Options

### MCPTxConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_timeout_ms` | int | 60000 | Default timeout for all operations (milliseconds) |
| `max_concurrent_requests` | int | 100 | Maximum parallel requests |
| `deduplication_window_ms` | int | 300000 | How long to remember request IDs (5 minutes) |
| `retry_policy` | RetryPolicy | See below | Default retry behavior |
| `enable_request_logging` | bool | False | Log all requests/responses |
| `log_level` | str | "INFO" | Logging verbosity |
| `max_message_size` | int | 10MB | Maximum message size |
| `enable_compression` | bool | False | Compress large messages |

### RetryPolicy Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_attempts` | int | 3 | Maximum retry attempts |
| `base_delay_ms` | int | 1000 | Initial retry delay (milliseconds) |
| `max_delay_ms` | int | 60000 | Maximum retry delay |
| `backoff_multiplier` | float | 2.0 | Exponential backoff factor |
| `jitter` | bool | True | Add randomness to prevent thundering herd |
| `retry_on_timeout` | bool | True | Retry timeout errors |

## FastMCP-Tx Configuration

### App-Level Configuration

```python
from mcp_tx import FastMCP-Tx, MCPTxConfig

# Configure FastMCP-Tx app
config = MCPTxConfig(
    default_timeout_ms=20000,
    enable_request_logging=True
)

app = FastMCP-Tx(
    mcp_session,
    config=config,
    name="Production App",
    max_tools=500  # Limit tool registry size
)
```

### Tool-Level Configuration

```python
@app.tool(
    # Custom retry for this tool
    retry_policy=RetryPolicy(
        max_attempts=5,
        base_delay_ms=2000
    ),
    
    # Tool-specific timeout
    timeout_ms=45000,
    
    # Custom idempotency
    idempotency_key_generator=lambda args: f"tool-{args['id']}"
)
async def critical_tool(id: str, data: dict) -> dict:
    """Tool with custom configuration."""
    return {"processed": True}
```

## Environment-Based Configuration

### Using Environment Variables

```python
import os
from mcp_tx import MCPTxConfig

# Read from environment
config = MCPTxConfig(
    default_timeout_ms=int(os.getenv("MCP-Tx_TIMEOUT", "30000")),
    max_concurrent_requests=int(os.getenv("MCP-Tx_MAX_CONCURRENT", "10")),
    enable_request_logging=os.getenv("MCP-Tx_LOGGING", "false").lower() == "true"
)
```

### Configuration File

```python
import json
from pathlib import Path
from mcp_tx import MCPTxConfig, RetryPolicy

# Load from JSON file
config_path = Path("rmcp_config.json")
if config_path.exists():
    with open(config_path) as f:
        config_data = json.load(f)
    
    config = MCPTxConfig(
        default_timeout_ms=config_data.get("timeout_ms", 30000),
        retry_policy=RetryPolicy(**config_data.get("retry", {})),
        **config_data.get("options", {})
    )
else:
    config = MCPTxConfig()  # Defaults
```

Example `rmcp_config.json`:
```json
{
  "timeout_ms": 30000,
  "retry": {
    "max_attempts": 5,
    "base_delay_ms": 1000,
    "backoff_multiplier": 2.0
  },
  "options": {
    "max_concurrent_requests": 20,
    "enable_request_logging": true
  }
}
```

## Advanced Configuration

### Custom Retry Strategies

```python
from mcp_tx import RetryPolicy

# Different strategies for different scenarios
AGGRESSIVE_RETRY = RetryPolicy(
    max_attempts=10,
    base_delay_ms=100,
    max_delay_ms=5000,
    backoff_multiplier=1.5
)

CONSERVATIVE_RETRY = RetryPolicy(
    max_attempts=3,
    base_delay_ms=5000,
    max_delay_ms=60000,
    backoff_multiplier=3.0
)

# Apply based on operation type
@app.tool(retry_policy=AGGRESSIVE_RETRY)
async def network_operation(): ...

@app.tool(retry_policy=CONSERVATIVE_RETRY)
async def expensive_operation(): ...
```

### Dynamic Configuration

```python
class DynamicMCPTxConfig:
    """Configuration that can be updated at runtime."""
    
    def __init__(self):
        self._config = MCPTxConfig()
        self._overrides = {}
    
    def update_timeout(self, operation: str, timeout_ms: int):
        """Update timeout for specific operations."""
        self._overrides[operation] = {"timeout_ms": timeout_ms}
    
    def get_config(self, operation: str) -> dict:
        """Get configuration for an operation."""
        base = self._config.__dict__.copy()
        base.update(self._overrides.get(operation, {}))
        return base

# Usage
dynamic_config = DynamicMCPTxConfig()
dynamic_config.update_timeout("slow_operation", 120000)  # 2 minutes
```

### Performance Tuning

```python
# High-throughput configuration
high_throughput_config = MCPTxConfig(
    max_concurrent_requests=50,
    default_timeout_ms=10000,  # Fail fast
    retry_policy=RetryPolicy(
        max_attempts=2,  # Minimal retries
        base_delay_ms=100
    ),
    enable_compression=True,  # Reduce bandwidth
    enable_request_logging=False  # Reduce overhead
)

# High-reliability configuration
high_reliability_config = MCPTxConfig(
    max_concurrent_requests=5,  # Limit load
    default_timeout_ms=60000,  # Patient timeouts
    retry_policy=RetryPolicy(
        max_attempts=10,  # Aggressive retry
        base_delay_ms=5000,
        jitter=True
    ),
    deduplication_window_ms=3600000,  # 1 hour
    enable_request_logging=True  # Full audit trail
)
```

## Monitoring Configuration

### Metrics Collection

```python
from mcp_tx import MCPTxConfig
import logging

# Configure with metrics
config = MCPTxConfig(
    enable_request_logging=True,
    log_level="DEBUG"
)

# Custom metrics handler
class MetricsHandler(logging.Handler):
    def emit(self, record):
        if hasattr(record, 'rmcp_metrics'):
            # Send to monitoring system
            metrics = record.rmcp_metrics
            send_to_prometheus(metrics)

# Attach to MCP-Tx logger
logger = logging.getLogger('rmcp')
logger.addHandler(MetricsHandler())
```

### Health Checks

```python
class HealthCheckConfig:
    """Configuration with built-in health monitoring."""
    
    def __init__(self, base_config: MCPTxConfig):
        self.base_config = base_config
        self.health_threshold = 0.95  # 95% success rate
        self.check_interval_ms = 30000  # 30 seconds
    
    async def health_check(self, session: MCPTxSession) -> bool:
        """Check if session is healthy."""
        try:
            result = await session.call_tool(
                "health_check",
                {},
                timeout_ms=5000
            )
            return result.rmcp_meta.ack
        except:
            return False
```

## Configuration Best Practices

### 1. Start with Defaults

```python
# Good: Use defaults unless you have specific requirements
config = MCPTxConfig()

# Only customize what you need
config.default_timeout_ms = 45000  # Specific requirement
```

### 2. Environment-Specific Settings

```python
# Development
dev_config = MCPTxConfig(
    enable_request_logging=True,
    log_level="DEBUG",
    retry_policy=RetryPolicy(max_attempts=1)  # Fail fast in dev
)

# Production
prod_config = MCPTxConfig(
    enable_request_logging=True,
    log_level="INFO",
    retry_policy=RetryPolicy(max_attempts=5),
    enable_compression=True
)
```

### 3. Document Your Choices

```python
# Configuration for high-frequency trading system
config = MCPTxConfig(
    # Low timeout because market data is time-sensitive
    default_timeout_ms=500,
    
    # No retries - stale data is worse than no data
    retry_policy=RetryPolicy(max_attempts=1),
    
    # High concurrency for parallel market queries
    max_concurrent_requests=100
)
```

## Troubleshooting Configuration

### Debug Mode

```python
# Enable all debugging features
debug_config = MCPTxConfig(
    enable_request_logging=True,
    log_level="DEBUG",
    # Slow down retries for debugging
    retry_policy=RetryPolicy(
        base_delay_ms=5000,
        jitter=False  # Predictable timing
    )
)
```

### Common Issues

1. **Timeouts too aggressive**
   ```python
   # Increase timeouts for slow operations
   config.default_timeout_ms = 120000  # 2 minutes
   ```

2. **Too many retries**
   ```python
   # Reduce retry attempts for user-facing operations
   config.retry_policy.max_attempts = 2
   ```

3. **Memory issues with deduplication**
   ```python
   # Reduce deduplication window
   config.deduplication_window_ms = 60000  # 1 minute
   ```

## See Also

- [Getting Started](getting-started.md) - Quick start guide
- [API Reference](api/mcp-tx-session.md) - Detailed API documentation
- [Performance Guide](performance.md) - Optimization tips

---

**Previous**: [Reliability Features](reliability-features.md) | **Next**: [Performance Guide](performance.md)