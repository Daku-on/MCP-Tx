# MCPTxSession API Reference

The main interface for reliable MCP tool calls.

## Class: MCPTxSession

```python
class MCPTxSession:
    """
    MCP-Tx Session that wraps an existing MCP session with reliability features.
    
    Provides:
    - ACK/NACK guarantees
    - Automatic retry with exponential backoff  
    - Request deduplication via idempotency keys
    - Transaction tracking
    - 100% backward compatibility with MCP
    """
```

### Constructor

```python
def __init__(self, mcp_session: BaseSession, config: MCPTxConfig | None = None)
```

**Parameters**:
- `mcp_session` (`BaseSession`): Existing MCP session to wrap
- `config` (`MCPTxConfig`, optional): MCP-Tx configuration. Defaults to `MCPTxConfig()`

**Example**:
```python
from mcp_tx import MCPTxSession, MCPTxConfig
from mcp.client.session import ClientSession

mcp_session = ClientSession(...)
config = MCPTxConfig(default_timeout_ms=10000)
rmcp_session = MCPTxSession(mcp_session, config)
```

### Methods

#### initialize()

```python
async def initialize(self, **kwargs) -> Any
```

Initialize the session with MCP-Tx capability negotiation.

**Parameters**:
- `**kwargs`: Passed through to underlying MCP session's `initialize()`

**Returns**: Result from underlying MCP session initialization

**Behavior**:
- Adds MCP-Tx experimental capabilities to initialization
- Detects server MCP-Tx support
- Enables/disables MCP-Tx features based on server capabilities

**Example**:
```python
result = await rmcp_session.initialize(
    capabilities={"tools": {"list_changed": True}}
)
print(f"MCP-Tx enabled: {rmcp_session.rmcp_enabled}")
```

#### call_tool()

```python
async def call_tool(
    self,
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    idempotency_key: str | None = None,
    timeout_ms: int | None = None,
    retry_policy: RetryPolicy | None = None,
) -> MCP-TxResult
```

Call a tool with MCP-Tx reliability guarantees.

**Parameters**:
- `name` (`str`): Tool name (alphanumeric, hyphens, underscores only)
- `arguments` (`dict[str, Any]`, optional): Tool arguments. Defaults to `{}`
- `idempotency_key` (`str`, optional): Unique key for deduplication
- `timeout_ms` (`int`, optional): Override default timeout (1-600,000ms)
- `retry_policy` (`RetryPolicy`, optional): Override default retry policy

**Returns**: `MCP-TxResult` with tool result and MCP-Tx metadata

**Raises**:
- `ValueError`: Invalid input parameters
- `MCP-TxTimeoutError`: Operation timed out
- `MCP-TxNetworkError`: Network/connection error
- `MCP-TxError`: Other MCP-Tx-specific errors

**Example**:
```python
# Basic tool call
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

# With idempotency
result = await rmcp_session.call_tool(
    "file_writer",
    {"path": "/output.txt", "content": "Hello"},
    idempotency_key="write-hello-v1"
)

# With custom retry and timeout
custom_retry = RetryPolicy(max_attempts=5, base_delay_ms=500)
result = await rmcp_session.call_tool(
    "api_call",
    {"url": "https://api.example.com"},
    retry_policy=custom_retry,
    timeout_ms=15000
)
```

#### close()

```python
async def close(self) -> None
```

Close the MCP-Tx session and underlying MCP session.

**Behavior**:
- Waits briefly for active requests to complete
- Closes underlying MCP session if it has a `close()` method
- Clears internal caches and request tracking

**Example**:
```python
await rmcp_session.close()

# Or use as async context manager
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    result = await rmcp.call_tool("echo", {"msg": "Hello"})
    # Automatically closed on exit
```

### Properties

#### rmcp_enabled

```python
@property
def rmcp_enabled(self) -> bool
```

Whether MCP-Tx features are enabled for this session.

**Returns**: `True` if server supports MCP-Tx, `False` if falling back to standard MCP

**Example**:
```python
await rmcp_session.initialize()
if rmcp_session.rmcp_enabled:
    print("✅ MCP-Tx features active")
else:
    print("⚠️ Falling back to standard MCP")
```

#### active_requests

```python
@property  
def active_requests(self) -> dict[str, RequestTracker]
```

Currently active MCP-Tx requests.

**Returns**: Dictionary mapping request IDs to `RequestTracker` objects

**Example**:
```python
print(f"Active requests: {len(rmcp_session.active_requests)}")
for request_id, tracker in rmcp_session.active_requests.items():
    print(f"  {request_id}: {tracker.status} ({tracker.attempts} attempts)")
```

### Async Context Manager

`MCPTxSession` supports async context manager protocol:

```python
async def __aenter__(self) -> MCPTxSession: ...
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

**Example**:
```python
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    
    result = await rmcp.call_tool("test", {})
    print(f"Result: {result.result}")
    
    # Session automatically closed on exit
```

## MCP-TxResult

Result object returned by `call_tool()`.

```python
@dataclass
class MCP-TxResult:
    """Result wrapper containing both MCP result and MCP-Tx metadata."""
    
    result: Any                    # Actual tool result from MCP
    rmcp_meta: MCP-TxResponse       # MCP-Tx metadata and status
```

### Properties

```python
@property
def ack(self) -> bool:
    """Whether the request was acknowledged."""
    return self.rmcp_meta.ack

@property  
def processed(self) -> bool:
    """Whether the tool was actually executed."""
    return self.rmcp_meta.processed

@property
def final_status(self) -> str:
    """Final status: 'completed' or 'failed'."""
    return self.rmcp_meta.final_status

@property
def attempts(self) -> int:
    """Number of retry attempts made."""
    return self.rmcp_meta.attempts
```

### Example Usage

```python
result = await rmcp_session.call_tool("calculator", {"op": "add", "a": 1, "b": 2})

# Check MCP-Tx guarantees
assert result.ack == True           # Request was acknowledged
assert result.processed == True     # Tool was executed  
assert result.final_status == "completed"
assert result.attempts >= 1         # At least one attempt

# Access actual result
if result.ack:
    calculation_result = result.result
    print(f"Sum: {calculation_result}")
else:
    print(f"Failed: {result.rmcp_meta.error_message}")
```

## Error Handling

### Exception Hierarchy

```python
MCP-TxError (base)
├── MCP-TxTimeoutError      # Timeout occurred
├── MCP-TxNetworkError      # Network/connection issue  
└── MCP-TxSequenceError     # Sequence/ordering error
```

### Error Attributes

All MCP-Tx errors have:
- `message`: Human-readable error description
- `error_code`: Machine-readable error code
- `retryable`: Whether error should trigger retry
- `details`: Additional error context

### Example Error Handling

```python
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError

try:
    result = await rmcp_session.call_tool("slow_api", {})
except MCP-TxTimeoutError as e:
    print(f"Timed out after {e.details['timeout_ms']}ms")
    # Maybe retry with longer timeout
except MCP-TxNetworkError as e:
    print(f"Network error: {e.message}")
    # Maybe check connection
except ValueError as e:
    print(f"Invalid input: {e}")
    # Fix the input parameters
```

## Best Practices

### 1. Resource Management

```python
# ✅ Good: Use async context manager
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    # ... use rmcp
    # Automatically cleaned up

# ⚠️ Acceptable: Manual cleanup  
rmcp = MCPTxSession(mcp_session)
try:
    await rmcp.initialize()
    # ... use rmcp
finally:
    await rmcp.close()
```

### 2. Idempotency Keys

```python
# ✅ Good: Use descriptive, unique keys
await rmcp.call_tool(
    "create_user",
    {"name": "Alice", "email": "alice@example.com"},
    idempotency_key="create-user-alice-2024-01-15"
)

# ❌ Bad: Generic or reused keys
await rmcp.call_tool(
    "create_user", 
    {...},
    idempotency_key="user"  # Too generic, will cause conflicts
)
```

### 3. Error Handling

```python
# ✅ Good: Specific error handling
try:
    result = await rmcp.call_tool("api_call", {})
except MCP-TxTimeoutError:
    # Handle timeout specifically
    result = await rmcp.call_tool("api_call", {}, timeout_ms=60000)
except MCP-TxNetworkError:
    # Handle network issues
    await asyncio.sleep(5)  # Wait and retry
    result = await rmcp.call_tool("api_call", {})

# ❌ Bad: Generic error handling
try:
    result = await rmcp.call_tool("api_call", {})
except Exception:
    pass  # Hides important error information
```

### 4. Configuration

```python
# ✅ Good: Environment-specific configuration
if environment == "production":
    config = MCPTxConfig(
        default_timeout_ms=30000,
        retry_policy=RetryPolicy(max_attempts=5),
        max_concurrent_requests=20
    )
else:
    config = MCPTxConfig(
        default_timeout_ms=5000, 
        retry_policy=RetryPolicy(max_attempts=2),
        max_concurrent_requests=5
    )

rmcp = MCPTxSession(mcp_session, config)
```

---

**Next**: [Configuration API](configuration.md) →