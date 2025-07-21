"""Test MCP-Tx session functionality."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import anyio
import pytest

from mcp_tx.session import MCPTxSession
from mcp_tx.types import MCPTxConfig, RetryPolicy


class MockMCPSession:
    """Mock MCP session for testing."""

    def __init__(self, should_fail: bool = False, supports_mcp_tx: bool = True):
        self.should_fail = should_fail
        self.supports_mcp_tx = supports_mcp_tx
        self.call_count = 0

    async def initialize(self, **kwargs) -> Any:
        """Mock initialize method."""
        capabilities = MagicMock()
        if self.supports_mcp_tx:
            capabilities.experimental = {"mcp_tx": {"version": "0.1.0"}}
        else:
            capabilities.experimental = {}

        result = MagicMock()
        result.capabilities = capabilities
        return result

    async def send_request(self, request: dict[str, Any]) -> Any:
        """Mock send_request method."""
        self.call_count += 1

        if self.should_fail and self.call_count <= 2:  # Fail first 2 attempts
            raise Exception("Network error")

        # Mock successful response
        return {"result": {"content": [{"type": "text", "text": "Tool executed successfully"}]}}


@pytest.mark.anyio
async def test_mcp_tx_session_initialization():
    """Test MCP-Tx session initialization with capability negotiation."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)

    # Initialize with basic capabilities
    result = await mcp_tx_session.initialize(capabilities={})

    # Should detect MCP-Tx support
    assert mcp_tx_session.mcp_tx_enabled is True
    assert result is not None


@pytest.mark.anyio
async def test_mcp_tx_session_fallback():
    """Test MCP-Tx session fallback when server doesn't support MCP-Tx."""
    mock_mcp = MockMCPSession(supports_mcp_tx=False)
    mcp_tx_session = MCPTxSession(mock_mcp)

    # Initialize
    await mcp_tx_session.initialize(capabilities={})

    # Should detect no MCP-Tx support
    assert mcp_tx_session.mcp_tx_enabled is False


@pytest.mark.anyio
async def test_successful_tool_call():
    """Test successful tool call with MCP-Tx."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)

    # Initialize
    await mcp_tx_session.initialize()

    # Call tool
    result = await mcp_tx_session.call_tool("test_tool", {"arg": "value"})

    # Verify result
    assert result.ack is True
    assert result.processed is True
    assert result.final_status == "completed"
    assert result.attempts == 1
    assert result.result is not None
    assert mock_mcp.call_count == 1


@pytest.mark.anyio
async def test_tool_call_with_retry():
    """Test tool call with automatic retry on failure."""
    mock_mcp = MockMCPSession(should_fail=True, supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)

    # Initialize
    await mcp_tx_session.initialize()

    # Configure retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay_ms=100,  # Short delay for testing
        backoff_multiplier=1.0,  # No backoff for testing
    )

    # Call tool (should succeed on 3rd attempt)
    result = await mcp_tx_session.call_tool("test_tool", {"arg": "value"}, retry_policy=retry_policy)

    # Verify result
    assert result.ack is True
    assert result.processed is True
    assert result.final_status == "completed"
    assert result.attempts == 3  # Should have retried
    assert mock_mcp.call_count == 3


@pytest.mark.anyio
async def test_tool_call_exhausted_retries():
    """Test tool call when all retries are exhausted."""
    mock_mcp = MockMCPSession(should_fail=True, supports_mcp_tx=True)
    # Make it always fail
    mock_mcp.call_count = 0

    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    # Configure retry policy with fewer attempts
    retry_policy = RetryPolicy(
        max_attempts=2,
        base_delay_ms=100,  # Minimum allowed delay
    )

    # Call tool (should fail after exhausting retries)
    result = await mcp_tx_session.call_tool("test_tool", {"arg": "value"}, retry_policy=retry_policy)

    # Verify failure result
    assert result.ack is False
    assert result.processed is False
    assert result.final_status == "failed"
    assert result.attempts == 2
    assert result.mcp_tx_meta.error_message is not None
    assert mock_mcp.call_count == 2


@pytest.mark.anyio
async def test_idempotency_key_deduplication():
    """Test request deduplication using idempotency keys."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    idempotency_key = "test-duplicate-key"

    # First call
    result1 = await mcp_tx_session.call_tool("test_tool", {"arg": "value1"}, idempotency_key=idempotency_key)

    # Second call with same idempotency key
    result2 = await mcp_tx_session.call_tool(
        "test_tool",
        {"arg": "value2"},  # Different args, but same key
        idempotency_key=idempotency_key,
    )

    # Verify first call succeeded
    assert result1.ack is True
    assert result1.mcp_tx_meta is not None
    assert result1.mcp_tx_meta.duplicate is False

    # Verify second call was deduplicated
    assert result2.ack is True  # Still successful
    assert result2.mcp_tx_meta is not None
    assert result2.mcp_tx_meta.duplicate is True  # But marked as duplicate

    # Should only have called MCP once
    assert mock_mcp.call_count == 1


@pytest.mark.anyio
async def test_timeout_handling():
    """Test timeout handling in tool calls."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)

    # Make the mock session slow
    original_send = mock_mcp.send_request

    async def slow_send_request(request):
        await anyio.sleep(0.2)  # 200ms delay
        return await original_send(request)

    mock_mcp.send_request = slow_send_request

    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    # Call with very short timeout
    result = await mcp_tx_session.call_tool(
        "test_tool",
        {"arg": "value"},
        timeout_ms=50,  # 50ms timeout, should fail
    )

    # Should have timed out
    assert result.ack is False
    assert result.processed is False
    assert result.final_status == "failed"
    assert result.mcp_tx_meta is not None
    assert result.mcp_tx_meta.error_message is not None
    assert "timeout" in result.mcp_tx_meta.error_message.lower()


@pytest.mark.anyio
async def test_concurrent_requests():
    """Test concurrent request handling."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    # Launch multiple concurrent requests
    async def run_tool_call(i):
        result = await mcp_tx_session.call_tool(f"test_tool_{i}", {"arg": f"value_{i}"})
        return result

    # Create and await coroutines concurrently using async nursery pattern
    results = []
    async with anyio.create_task_group() as tg:

        async def collect_result(i):
            result = await mcp_tx_session.call_tool(f"test_tool_{i}", {"arg": f"value_{i}"})
            results.append((i, result))

        for i in range(5):
            tg.start_soon(collect_result, i)

    # Sort results by index to maintain order
    results.sort(key=lambda x: x[0])
    results = [result for _, result in results]

    # All should succeed
    for i, result in enumerate(results):
        assert result.ack is True
        assert result.processed is True
        assert result.final_status == "completed"

    # Should have called MCP for each request
    assert mock_mcp.call_count == 5


def test_mcp_tx_config_custom():
    """Test custom MCP-Tx configuration."""
    config = MCPTxConfig(default_timeout_ms=60000, max_concurrent_requests=20, retry_policy=RetryPolicy(max_attempts=5))

    mock_mcp = MockMCPSession()
    mcp_tx_session = MCPTxSession(mock_mcp, config)

    assert mcp_tx_session.config.default_timeout_ms == 60000
    assert mcp_tx_session.config.max_concurrent_requests == 20
    assert mcp_tx_session.config.retry_policy.max_attempts == 5


@pytest.mark.anyio
async def test_session_close():
    """Test session cleanup on close."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mock_mcp.close = AsyncMock()  # Add close method

    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    # Add some state
    await mcp_tx_session.call_tool("test_tool", {})

    # Close session
    await mcp_tx_session.close()

    # Verify cleanup
    assert len(mcp_tx_session.active_requests) == 0
    mock_mcp.close.assert_called_once()


@pytest.mark.anyio
async def test_input_validation():
    """Test input validation for tool calls."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mcp_tx_session = MCPTxSession(mock_mcp)
    await mcp_tx_session.initialize()

    # Test invalid tool names
    with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
        await mcp_tx_session.call_tool("", {})

    with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
        await mcp_tx_session.call_tool("   ", {})

    with pytest.raises(ValueError, match="alphanumeric characters"):
        await mcp_tx_session.call_tool("invalid@tool", {})

    # Test invalid arguments
    with pytest.raises(ValueError, match="must be a dictionary"):
        await mcp_tx_session.call_tool("test_tool", "invalid")

    # Test invalid timeout
    with pytest.raises(ValueError, match="Timeout must be between"):
        await mcp_tx_session.call_tool("test_tool", {}, timeout_ms=0)

    with pytest.raises(ValueError, match="Timeout must be between"):
        await mcp_tx_session.call_tool("test_tool", {}, timeout_ms=7300000)

    # Test invalid idempotency key
    with pytest.raises(ValueError, match="non-empty string"):
        await mcp_tx_session.call_tool("test_tool", {}, idempotency_key="")


@pytest.mark.anyio
async def test_async_context_manager():
    """Test async context manager support."""
    mock_mcp = MockMCPSession(supports_mcp_tx=True)
    mock_mcp.close = AsyncMock()

    async with MCPTxSession(mock_mcp) as mcp_tx_session:
        await mcp_tx_session.initialize()
        result = await mcp_tx_session.call_tool("test_tool", {})
        assert result.ack is True

    # Session should be closed automatically
    mock_mcp.close.assert_called_once()
