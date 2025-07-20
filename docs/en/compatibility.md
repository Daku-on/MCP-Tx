# RMCP Compatibility Guide

This guide covers compatibility between RMCP and standard MCP, version requirements, and migration considerations.

## MCP Compatibility

### Full Backward Compatibility

RMCP is 100% backward compatible with standard MCP:

```python
# Works with any MCP server
async def use_with_any_mcp_server(mcp_session):
    # RMCP wraps existing sessions
    rmcp_session = RMCPSession(mcp_session)
    
    # If server doesn't support RMCP, it works like standard MCP
    result = await rmcp_session.call_tool("any_tool", {})
    
    # RMCP features are optional
    if hasattr(result, 'rmcp_meta'):
        print(f"RMCP enabled: {result.rmcp_meta.ack}")
    else:
        print("Standard MCP response")
```

### Feature Detection

```python
async def detect_rmcp_support(session):
    """Check if server supports RMCP features."""
    # During initialization, RMCP negotiates capabilities
    info = await session.initialize()
    
    if 'experimental' in info.capabilities:
        rmcp = info.capabilities['experimental'].get('rmcp', {})
        return {
            'supported': bool(rmcp),
            'version': rmcp.get('version'),
            'features': rmcp.get('features', [])
        }
    
    return {'supported': False}
```

## Version Requirements

### Python Version Support

| Python Version | RMCP Support | Notes |
|---------------|--------------|-------|
| 3.10+ | ✅ Full support | Recommended |
| 3.9 | ✅ Full support | Supported |
| 3.8 | ⚠️ Limited | Type hints may need adjustment |
| 3.7 or below | ❌ Not supported | Requires modern async features |

### MCP SDK Versions

| MCP SDK Version | RMCP Compatibility | Notes |
|-----------------|-------------------|-------|
| 1.0.0+ | ✅ Full support | Current standard |
| 0.9.x | ✅ Compatible | Some features may be limited |
| 0.8.x or below | ⚠️ Partial | Core features only |

### Dependency Versions

```toml
# pyproject.toml
[dependencies]
mcp-python-sdk = ">=1.0.0"
pydantic = ">=2.0.0"
anyio = ">=3.0.0"  # For cross-platform async
```

## Protocol Compatibility

### RMCP Protocol Versions

```python
# RMCP supports multiple protocol versions
PROTOCOL_VERSIONS = {
    "0.1.0": {  # Current version
        "features": ["ack", "retry", "idempotency"],
        "compatible_with": ["0.1.x"]
    },
    "0.2.0": {  # Future version
        "features": ["ack", "retry", "idempotency", "transactions"],
        "compatible_with": ["0.1.x", "0.2.x"]
    }
}
```

### Capability Negotiation

```typescript
// Client announces supported versions
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "min_version": "0.1.0",
        "features": ["ack", "retry", "idempotency"]
      }
    }
  }
}

// Server responds with its capabilities
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "features": ["ack", "retry"]  // Server may support subset
      }
    }
  }
}
```

## Framework Compatibility

### Async Framework Support

```python
# RMCP uses anyio for cross-platform async
import anyio

# Works with asyncio (default)
import asyncio
app = FastRMCP(mcp_session)  # Uses asyncio

# Also works with trio
import trio
async def with_trio():
    async with anyio.create_task_group() as tg:
        app = FastRMCP(mcp_session)
        tg.start_soon(app.initialize)
```

### Web Framework Compatibility

| Framework | Supported | Integration Method |
|-----------|-----------|-------------------|
| FastAPI | ✅ Native async | Direct integration |
| Django | ✅ Via async views | async_to_sync wrapper |
| Flask | ✅ With extensions | Event loop management |
| Tornado | ✅ Native async | Direct integration |
| aiohttp | ✅ Native async | Direct integration |

## Operating System Compatibility

### Platform Support

| Platform | Support Level | Notes |
|----------|--------------|-------|
| Linux | ✅ Full support | All features available |
| macOS | ✅ Full support | All features available |
| Windows | ✅ Full support | Requires Python 3.8+ for better async |
| WSL | ✅ Full support | Tested on WSL2 |

### Platform-Specific Considerations

```python
import sys
from rmcp import RMCPConfig

def get_platform_config() -> RMCPConfig:
    """Get platform-optimized configuration."""
    if sys.platform == "win32":
        # Windows-specific optimizations
        return RMCPConfig(
            max_concurrent_requests=50,  # Windows has different limits
            use_uvloop=False  # Not available on Windows
        )
    else:
        # Unix-like systems
        return RMCPConfig(
            max_concurrent_requests=100,
            use_uvloop=True  # Better performance
        )
```

## Breaking Changes and Migration

### From RMCP 0.x to 1.0

```python
# Old API (0.x)
result = await rmcp.call_tool("my_tool", {})
if result.acknowledged:  # Changed
    print(result.retry_count)  # Changed

# New API (1.0)
result = await rmcp.call_tool("my_tool", {})
if result.rmcp_meta.ack:  # New structure
    print(result.rmcp_meta.attempts)  # Renamed
```

### Migration Helper

```python
class CompatibilityWrapper:
    """Wrapper for backward compatibility."""
    
    def __init__(self, rmcp_result):
        self._result = rmcp_result
    
    # Old property names for compatibility
    @property
    def acknowledged(self):
        return self._result.rmcp_meta.ack
    
    @property
    def retry_count(self):
        return self._result.rmcp_meta.attempts - 1
    
    @property
    def result(self):
        return self._result.result

# Usage
def make_compatible(result):
    """Convert new result to old format."""
    return CompatibilityWrapper(result)
```

## Known Compatibility Issues

### 1. Type Hints in Python 3.8

```python
# Python 3.9+ syntax
def process(data: dict[str, Any]) -> list[str]:
    pass

# Python 3.8 compatible
from typing import Dict, List, Any

def process(data: Dict[str, Any]) -> List[str]:
    pass
```

### 2. AsyncIO on Windows

```python
# Windows requires special handling for Python < 3.8
import sys
import asyncio

if sys.platform == "win32" and sys.version_info < (3, 8):
    # Set event loop policy for Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### 3. Large Message Handling

```python
# Some MCP servers have message size limits
config = RMCPConfig(
    max_message_size=1024 * 1024,  # 1MB limit
    enable_compression=True  # Compress large messages
)

# Check message size before sending
async def safe_call_tool(app, name, arguments):
    arg_size = len(json.dumps(arguments))
    if arg_size > 1024 * 1024:
        raise ValueError(f"Arguments too large: {arg_size} bytes")
    
    return await app.call_tool(name, arguments)
```

## Testing Compatibility

### Compatibility Test Suite

```python
import pytest
from rmcp import FastRMCP, RMCPSession

@pytest.mark.compatibility
class TestCompatibility:
    """Test RMCP compatibility with various configurations."""
    
    async def test_standard_mcp_fallback(self, standard_mcp_session):
        """Test RMCP works with non-RMCP servers."""
        rmcp = RMCPSession(standard_mcp_session)
        
        # Should work without RMCP features
        result = await rmcp.call_tool("echo", {"text": "hello"})
        assert result.result == {"text": "hello"}
        
        # RMCP metadata should indicate fallback
        assert not hasattr(result, 'rmcp_meta') or not result.rmcp_meta.ack
    
    async def test_version_negotiation(self, mock_server):
        """Test protocol version negotiation."""
        # Server supports older version
        mock_server.capabilities = {
            "experimental": {
                "rmcp": {"version": "0.0.9"}
            }
        }
        
        session = await connect_to_server(mock_server)
        assert session.rmcp_version == "0.0.9"  # Use server version
    
    async def test_feature_degradation(self, limited_server):
        """Test graceful feature degradation."""
        # Server only supports ACK, not retry
        app = FastRMCP(limited_server)
        
        @app.tool(retry_policy=RetryPolicy(max_attempts=3))
        async def test_tool():
            return "success"
        
        # Should work but without retry
        result = await app.call_tool("test_tool", {})
        assert result.rmcp_meta.attempts == 1  # No retry occurred
```

### Compatibility Checker Tool

```python
# rmcp_check.py
async def check_compatibility(server_url: str):
    """Check RMCP compatibility with a server."""
    try:
        # Connect to server
        session = await connect_to_mcp_server(server_url)
        
        # Check capabilities
        rmcp_support = await detect_rmcp_support(session)
        
        print(f"Server: {server_url}")
        print(f"RMCP Support: {'Yes' if rmcp_support['supported'] else 'No'}")
        
        if rmcp_support['supported']:
            print(f"Version: {rmcp_support['version']}")
            print(f"Features: {', '.join(rmcp_support['features'])}")
        
        # Test basic operations
        print("\nTesting basic operations...")
        
        # Test tool call
        try:
            result = await session.call_tool("ping", {})
            print("✓ Tool calls: Supported")
        except:
            print("✗ Tool calls: Not supported")
        
        # Test RMCP features if available
        if rmcp_support['supported']:
            rmcp_session = RMCPSession(session)
            
            # Test ACK
            result = await rmcp_session.call_tool("ping", {})
            if hasattr(result, 'rmcp_meta') and result.rmcp_meta.ack:
                print("✓ ACK/NACK: Supported")
            else:
                print("✗ ACK/NACK: Not supported")
        
        await session.close()
        
    except Exception as e:
        print(f"Error checking compatibility: {e}")

# Run compatibility check
if __name__ == "__main__":
    import sys
    asyncio.run(check_compatibility(sys.argv[1]))
```

## Future Compatibility

### Planned Features

RMCP is designed to be forward-compatible:

```python
# Future features will be optional
future_config = RMCPConfig(
    # Current features
    enable_retry=True,
    enable_deduplication=True,
    
    # Future features (ignored by current version)
    enable_transactions=True,  # Future
    enable_streaming=True,     # Future
    enable_batching=True       # Future
)
```

### Version Policy

- **Major versions** (1.0, 2.0): May have breaking changes
- **Minor versions** (1.1, 1.2): New features, backward compatible
- **Patch versions** (1.0.1, 1.0.2): Bug fixes only

## See Also

- [Migration Guide](migration.md) - Upgrading from MCP to RMCP
- [Getting Started](getting-started.md) - Initial setup
- [FAQ](faq.md) - Common compatibility questions

---

**Previous**: [Migration Guide](migration.md) | **Next**: [FAQ](faq.md)