"""Test RMCP session functionality."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from rmcp.session import RMCPSession
from rmcp.types import RetryPolicy, RMCPConfig


class MockMCPSession:
    """Mock MCP session for testing."""

    def __init__(self, should_fail: bool = False, supports_rmcp: bool = True):
        self.should_fail = should_fail
        self.supports_rmcp = supports_rmcp
        self.call_count = 0

    async def initialize(self, **kwargs) -> Any:
        """Mock initialize method."""
        capabilities = MagicMock()
        if self.supports_rmcp:
            capabilities.experimental = {"rmcp": {"version": "0.1.0"}}
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
async def test_rmcp_session_initialization():
    """Test RMCP session initialization with capability negotiation."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)

    # Initialize with basic capabilities
    result = await rmcp_session.initialize(capabilities={})

    # Should detect RMCP support
    assert rmcp_session.rmcp_enabled is True
    assert result is not None


@pytest.mark.anyio
async def test_rmcp_session_fallback():
    """Test RMCP session fallback when server doesn't support RMCP."""
    mock_mcp = MockMCPSession(supports_rmcp=False)
    rmcp_session = RMCPSession(mock_mcp)

    # Initialize
    await rmcp_session.initialize(capabilities={})

    # Should detect no RMCP support
    assert rmcp_session.rmcp_enabled is False


@pytest.mark.anyio
async def test_successful_tool_call():
    """Test successful tool call with RMCP."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)

    # Initialize
    await rmcp_session.initialize()

    # Call tool
    result = await rmcp_session.call_tool("test_tool", {"arg": "value"})

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
    mock_mcp = MockMCPSession(should_fail=True, supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)

    # Initialize
    await rmcp_session.initialize()

    # Configure retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        base_delay_ms=100,  # Short delay for testing
        backoff_multiplier=1.0,  # No backoff for testing
    )

    # Call tool (should succeed on 3rd attempt)
    result = await rmcp_session.call_tool("test_tool", {"arg": "value"}, retry_policy=retry_policy)

    # Verify result
    assert result.ack is True
    assert result.processed is True
    assert result.final_status == "completed"
    assert result.attempts == 3  # Should have retried
    assert mock_mcp.call_count == 3


@pytest.mark.anyio
async def test_tool_call_exhausted_retries():
    """Test tool call when all retries are exhausted."""
    mock_mcp = MockMCPSession(should_fail=True, supports_rmcp=True)
    # Make it always fail
    mock_mcp.call_count = 0

    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    # Configure retry policy with fewer attempts
    retry_policy = RetryPolicy(
        max_attempts=2,
        base_delay_ms=100,  # Minimum allowed delay
    )

    # Call tool (should fail after exhausting retries)
    result = await rmcp_session.call_tool("test_tool", {"arg": "value"}, retry_policy=retry_policy)

    # Verify failure result
    assert result.ack is False
    assert result.processed is False
    assert result.final_status == "failed"
    assert result.attempts == 2
    assert result.rmcp_meta.error_message is not None
    assert mock_mcp.call_count == 2


@pytest.mark.anyio
async def test_idempotency_key_deduplication():
    """Test request deduplication using idempotency keys."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    idempotency_key = "test-duplicate-key"

    # First call
    result1 = await rmcp_session.call_tool("test_tool", {"arg": "value1"}, idempotency_key=idempotency_key)

    # Second call with same idempotency key
    result2 = await rmcp_session.call_tool(
        "test_tool",
        {"arg": "value2"},  # Different args, but same key
        idempotency_key=idempotency_key,
    )

    # Verify first call succeeded
    assert result1.ack is True
    assert result1.rmcp_meta is not None
    assert result1.rmcp_meta.duplicate is False

    # Verify second call was deduplicated
    assert result2.ack is True  # Still successful
    assert result2.rmcp_meta is not None
    assert result2.rmcp_meta.duplicate is True  # But marked as duplicate

    # Should only have called MCP once
    assert mock_mcp.call_count == 1


@pytest.mark.anyio
async def test_timeout_handling():
    """Test timeout handling in tool calls."""
    mock_mcp = MockMCPSession(supports_rmcp=True)

    # Make the mock session slow
    original_send = mock_mcp.send_request

    async def slow_send_request(request):
        await asyncio.sleep(0.2)  # 200ms delay
        return await original_send(request)

    mock_mcp.send_request = slow_send_request

    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    # Call with very short timeout
    result = await rmcp_session.call_tool(
        "test_tool",
        {"arg": "value"},
        timeout_ms=50,  # 50ms timeout, should fail
    )

    # Should have timed out
    assert result.ack is False
    assert result.processed is False
    assert result.final_status == "failed"
    assert result.rmcp_meta is not None
    assert result.rmcp_meta.error_message is not None
    assert "timeout" in result.rmcp_meta.error_message.lower()


@pytest.mark.anyio
async def test_concurrent_requests():
    """Test concurrent request handling."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    # Launch multiple concurrent requests
    tasks = []
    for i in range(5):
        task = rmcp_session.call_tool(f"test_tool_{i}", {"arg": f"value_{i}"})
        tasks.append(task)

    # Wait for all to complete
    results = await asyncio.gather(*tasks)

    # All should succeed
    for i, result in enumerate(results):
        assert result.ack is True
        assert result.processed is True
        assert result.final_status == "completed"

    # Should have called MCP for each request
    assert mock_mcp.call_count == 5


def test_rmcp_config_custom():
    """Test custom RMCP configuration."""
    config = RMCPConfig(default_timeout_ms=60000, max_concurrent_requests=20, retry_policy=RetryPolicy(max_attempts=5))

    mock_mcp = MockMCPSession()
    rmcp_session = RMCPSession(mock_mcp, config)

    assert rmcp_session.config.default_timeout_ms == 60000
    assert rmcp_session.config.max_concurrent_requests == 20
    assert rmcp_session.config.retry_policy.max_attempts == 5


@pytest.mark.anyio
async def test_session_close():
    """Test session cleanup on close."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    mock_mcp.close = AsyncMock()  # Add close method

    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    # Add some state
    await rmcp_session.call_tool("test_tool", {})

    # Close session
    await rmcp_session.close()

    # Verify cleanup
    assert len(rmcp_session.active_requests) == 0
    mock_mcp.close.assert_called_once()


@pytest.mark.anyio
async def test_input_validation():
    """Test input validation for tool calls."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()

    # Test invalid tool names
    with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
        await rmcp_session.call_tool("", {})

    with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
        await rmcp_session.call_tool("   ", {})

    with pytest.raises(ValueError, match="alphanumeric characters"):
        await rmcp_session.call_tool("invalid@tool", {})

    # Test invalid arguments
    with pytest.raises(ValueError, match="must be a dictionary"):
        await rmcp_session.call_tool("test_tool", "invalid")

    # Test invalid timeout
    with pytest.raises(ValueError, match="Timeout must be between"):
        await rmcp_session.call_tool("test_tool", {}, timeout_ms=0)

    with pytest.raises(ValueError, match="Timeout must be between"):
        await rmcp_session.call_tool("test_tool", {}, timeout_ms=700000)

    # Test invalid idempotency key
    with pytest.raises(ValueError, match="non-empty string"):
        await rmcp_session.call_tool("test_tool", {}, idempotency_key="")


@pytest.mark.anyio
async def test_async_context_manager():
    """Test async context manager support."""
    mock_mcp = MockMCPSession(supports_rmcp=True)
    mock_mcp.close = AsyncMock()

    async with RMCPSession(mock_mcp) as rmcp_session:
        await rmcp_session.initialize()
        result = await rmcp_session.call_tool("test_tool", {})
        assert result.ack is True

    # Session should be closed automatically
    mock_mcp.close.assert_called_once()
