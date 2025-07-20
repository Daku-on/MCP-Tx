"""Tests for FastRMCP decorator-based API."""

from unittest.mock import AsyncMock

import anyio
import pytest

from rmcp import FastRMCP, RetryPolicy, RMCPResponse, RMCPResult


class TestFastRMCP:
    """Test FastRMCP decorator functionality."""

    @pytest.fixture
    def mock_mcp_session(self):
        """Create a mock MCP session."""
        session = AsyncMock()
        session.call_tool = AsyncMock()
        return session

    @pytest.fixture
    async def fastrmcp_app(self, mock_mcp_session):
        """Create FastRMCP app with mock session."""
        app = FastRMCP(mock_mcp_session, name="Test App")
        await app.initialize()
        return app

    def test_fastrmcp_creation(self, mock_mcp_session):
        """Test FastRMCP app creation."""
        app = FastRMCP(mock_mcp_session, name="Test App")
        assert app.name == "Test App"
        assert not app._initialized
        assert app.list_tools() == []

    def test_tool_decorator_basic(self, mock_mcp_session):
        """Test basic tool registration with decorator."""
        app = FastRMCP(mock_mcp_session)

        @app.tool()
        def simple_tool(x: int) -> str:
            """A simple tool."""
            return str(x)

        # Tool should be registered
        assert "simple_tool" in app.list_tools()

        # Tool info should be available
        info = app.get_tool_info("simple_tool")
        assert info is not None
        assert info["name"] == "simple_tool"
        assert info["description"] == "A simple tool."
        assert not info["is_async"]
        assert not info["has_retry_policy"]

    def test_tool_decorator_async(self, mock_mcp_session):
        """Test async tool registration."""
        app = FastRMCP(mock_mcp_session)

        @app.tool()
        async def async_tool(data: dict) -> dict:
            """An async tool."""
            return {"processed": data}

        # Tool should be registered as async
        info = app.get_tool_info("async_tool")
        assert info is not None
        assert info["is_async"]

    def test_tool_decorator_with_options(self, mock_mcp_session):
        """Test tool registration with custom options."""
        retry_policy = RetryPolicy(max_attempts=5, base_delay_ms=2000)

        app = FastRMCP(mock_mcp_session)

        @app.tool(
            name="custom_tool", retry_policy=retry_policy, timeout_ms=30000, description="Custom tool description"
        )
        def tool_func(arg: str) -> str:
            return f"Result: {arg}"

        # Tool should be registered with custom name
        assert "custom_tool" in app.list_tools()
        assert "tool_func" not in app.list_tools()

        # Tool info should reflect custom options
        info = app.get_tool_info("custom_tool")
        assert info is not None
        assert info["description"] == "Custom tool description"
        assert info["has_retry_policy"]
        assert info["timeout_ms"] == 30000

    def test_tool_decorator_wrong_usage(self, mock_mcp_session):
        """Test error handling for incorrect decorator usage."""
        app = FastRMCP(mock_mcp_session)

        with pytest.raises(TypeError, match="requires parentheses"):

            @app.tool
            def bad_tool():
                pass

    @pytest.mark.anyio
    async def test_call_tool_success(self, fastrmcp_app, mock_mcp_session):
        """Test successful tool call through FastRMCP."""

        # Register a tool
        @fastrmcp_app.tool()
        def test_tool(x: int) -> str:
            return str(x)

        # Mock RMCP session response
        fastrmcp_app._rmcp_session.call_tool = AsyncMock(
            return_value=RMCPResult(
                result={"output": "42"},
                rmcp_meta=RMCPResponse(ack=True, processed=True, duplicate=False, attempts=1, final_status="success"),
            )
        )

        # Call tool
        result = await fastrmcp_app.call_tool("test_tool", {"x": 42})

        # Verify call was made with correct parameters
        fastrmcp_app._rmcp_session.call_tool.assert_called_once_with(
            name="test_tool",
            arguments={"x": 42},
            retry_policy=None,
            timeout_ms=None,
            idempotency_key=None,
        )

        # Verify result
        assert result.rmcp_meta.ack
        assert result.result == {"output": "42"}

    @pytest.mark.anyio
    async def test_call_tool_with_custom_policies(self, fastrmcp_app):
        """Test tool call with custom retry policy and timeout."""
        retry_policy = RetryPolicy(max_attempts=3, base_delay_ms=1000)

        # Register tool with custom policies
        @fastrmcp_app.tool(retry_policy=retry_policy, timeout_ms=15000)
        def custom_tool(data: str) -> str:
            return data.upper()

        # Mock RMCP session response
        fastrmcp_app._rmcp_session.call_tool = AsyncMock(
            return_value=RMCPResult(
                result={"output": "HELLO"},
                rmcp_meta=RMCPResponse(ack=True, processed=True, duplicate=False, attempts=2, final_status="success"),
            )
        )

        # Call tool
        result = await fastrmcp_app.call_tool("custom_tool", {"data": "hello"})

        # Verify custom policies were passed
        fastrmcp_app._rmcp_session.call_tool.assert_called_once_with(
            name="custom_tool",
            arguments={"data": "hello"},
            retry_policy=retry_policy,
            timeout_ms=15000,
            idempotency_key=None,
        )

        assert result.rmcp_meta.attempts == 2

    @pytest.mark.anyio
    async def test_call_tool_with_idempotency_key_generator(self, fastrmcp_app):
        """Test tool call with custom idempotency key generator."""

        def generate_key(args: dict) -> str:
            return f"custom-{args['id']}-{args['action']}"

        # Register tool with idempotency key generator
        @fastrmcp_app.tool(idempotency_key_generator=generate_key)
        def idempotent_tool(id: str, action: str) -> str:
            return f"Processed {action} for {id}"

        # Mock RMCP session response
        fastrmcp_app._rmcp_session.call_tool = AsyncMock(
            return_value=RMCPResult(
                result={"output": "Processed update for user123"},
                rmcp_meta=RMCPResponse(ack=True, processed=True, duplicate=False, attempts=1, final_status="success"),
            )
        )

        # Call tool
        arguments = {"id": "user123", "action": "update"}
        await fastrmcp_app.call_tool("idempotent_tool", arguments)

        # Verify generated idempotency key was used
        fastrmcp_app._rmcp_session.call_tool.assert_called_once_with(
            name="idempotent_tool",
            arguments=arguments,
            retry_policy=None,
            timeout_ms=None,
            idempotency_key="custom-user123-update",
        )

    @pytest.mark.anyio
    async def test_call_tool_not_registered(self, fastrmcp_app):
        """Test error when calling unregistered tool."""
        with pytest.raises(ValueError, match="Tool 'nonexistent' not registered"):
            await fastrmcp_app.call_tool("nonexistent", {})

    @pytest.mark.anyio
    async def test_call_tool_not_initialized(self, mock_mcp_session):
        """Test error when calling tool before initialization."""
        app = FastRMCP(mock_mcp_session)

        @app.tool()
        def test_tool():
            return "test"

        with pytest.raises(RuntimeError, match="FastRMCP not initialized"):
            await app.call_tool("test_tool", {})

    @pytest.mark.anyio
    async def test_context_manager(self, mock_mcp_session):
        """Test FastRMCP as async context manager."""
        app = FastRMCP(mock_mcp_session, name="Context Test")

        assert not app._initialized

        async with app:
            assert app._initialized

            @app.tool()
            def context_tool() -> str:
                return "works"

            # Should be able to call tools within context
            app._rmcp_session.call_tool = AsyncMock(
                return_value=RMCPResult(
                    result={"output": "works"},
                    rmcp_meta=RMCPResponse(
                        ack=True, processed=True, duplicate=False, attempts=1, final_status="success"
                    ),
                )
            )

            result = await app.call_tool("context_tool", {})
            assert result.rmcp_meta.ack

    def test_get_all_tools_info(self, mock_mcp_session):
        """Test getting information about all registered tools."""
        app = FastRMCP(mock_mcp_session)

        @app.tool()
        def tool1(x: int) -> str:
            """First tool."""
            return str(x)

        @app.tool(retry_policy=RetryPolicy(max_attempts=3))
        async def tool2(data: dict) -> dict:
            """Second tool."""
            return data

        all_info = app.get_all_tools_info()

        assert len(all_info) == 2
        assert "tool1" in all_info
        assert "tool2" in all_info

        assert all_info["tool1"]["description"] == "First tool."
        assert not all_info["tool1"]["is_async"]
        assert not all_info["tool1"]["has_retry_policy"]

        assert all_info["tool2"]["description"] == "Second tool."
        assert all_info["tool2"]["is_async"]
        assert all_info["tool2"]["has_retry_policy"]

    def test_tool_registry_size_limit(self, mock_mcp_session):
        """Test tool registry size limit enforcement."""
        app = FastRMCP(mock_mcp_session, max_tools=2)

        @app.tool()
        def tool1() -> str:
            return "tool1"

        @app.tool()
        def tool2() -> str:
            return "tool2"

        # Third tool should raise error
        with pytest.raises(ValueError, match="Registry full"):

            @app.tool()
            def tool3() -> str:
                return "tool3"

    def test_tool_name_collision(self, mock_mcp_session):
        """Test tool name collision detection."""
        app = FastRMCP(mock_mcp_session)

        @app.tool()
        def duplicate_tool() -> str:
            return "first"

        # Second tool with same name should raise error
        with pytest.raises(ValueError, match="already registered"):

            @app.tool(name="duplicate_tool")
            def another_duplicate_tool() -> str:  # Different function, same tool name
                return "second"

    @pytest.mark.anyio
    async def test_concurrent_initialization(self, mock_mcp_session):
        """Test concurrent initialization safety."""
        app = FastRMCP(mock_mcp_session)

        # Start multiple initialization tasks concurrently
        async with anyio.create_task_group() as tg:
            for _ in range(5):
                tg.start_soon(app.initialize)

        # Should only be initialized once
        assert app._initialized

    @pytest.mark.anyio
    async def test_get_all_tools_info_with_none_values(self, fastrmcp_app):
        """Test get_all_tools_info handles None values correctly."""

        @fastrmcp_app.tool()
        def test_tool() -> str:
            return "test"

        # Mock get_tool_info to return None for some tools
        original_get_tool_info = fastrmcp_app.get_tool_info

        def mock_get_tool_info(name: str):
            if name == "test_tool":
                return original_get_tool_info(name)
            return None

        fastrmcp_app.get_tool_info = mock_get_tool_info

        all_info = fastrmcp_app.get_all_tools_info()

        # Should only include tools with non-None info
        assert "test_tool" in all_info
        assert len(all_info) == 1

    @pytest.mark.anyio
    async def test_concurrent_tool_calls(self, fastrmcp_app):
        """Test concurrent tool calls for thread safety."""

        @fastrmcp_app.tool()
        def concurrent_tool(value: int) -> int:
            return value * 2

        # Mock RMCP session response
        fastrmcp_app._rmcp_session.call_tool = AsyncMock(
            side_effect=lambda name, arguments, **kwargs: RMCPResult(
                result={"output": arguments["value"] * 2},
                rmcp_meta=RMCPResponse(ack=True, processed=True, duplicate=False, attempts=1, final_status="success"),
            )
        )

        # Execute multiple concurrent tool calls
        async def make_concurrent_call(value: int):
            return await fastrmcp_app.call_tool("concurrent_tool", {"value": value})

        # Start 10 concurrent calls
        async with anyio.create_task_group() as tg:
            for i in range(10):
                tg.start_soon(make_concurrent_call, i)

        # Verify RMCP session was called for each task
        assert fastrmcp_app._rmcp_session.call_tool.call_count == 10

    @pytest.mark.anyio
    async def test_deep_copy_protection(self, fastrmcp_app):
        """Test that tool configurations are protected from mutation."""

        @fastrmcp_app.tool(timeout_ms=5000)
        def protected_tool() -> str:
            return "protected"

        # Get tool config twice
        config1 = fastrmcp_app._registry.get_tool("protected_tool")
        config2 = fastrmcp_app._registry.get_tool("protected_tool")

        # They should be separate objects
        assert config1 is not config2

        # Modifying one shouldn't affect the other
        if config1:
            config1["timeout_ms"] = 9999

        if config2:
            assert config2["timeout_ms"] == 5000  # Should remain unchanged

    def test_optimized_get_all_tools_info_performance(self, mock_mcp_session):
        """Test that get_all_tools_info is efficiently implemented."""
        app = FastRMCP(mock_mcp_session)

        # Register multiple tools
        for i in range(100):

            @app.tool(name=f"tool_{i}", timeout_ms=1000 + i)
            def test_tool() -> str:
                return f"tool_{i}"

        # This should be efficient (single dict iteration, not multiple lookups)
        all_info = app.get_all_tools_info()

        assert len(all_info) == 100
        for i in range(100):
            tool_name = f"tool_{i}"
            assert tool_name in all_info
            assert all_info[tool_name]["timeout_ms"] == 1000 + i

    @pytest.mark.anyio
    async def test_input_validation(self, fastrmcp_app):
        """Test input validation for call_tool method."""

        @fastrmcp_app.tool()
        def test_tool(x: int) -> str:
            return str(x)

        # Test invalid tool name
        with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
            await fastrmcp_app.call_tool("", {"x": 1})

        with pytest.raises(ValueError, match="Tool name must be a non-empty string"):
            await fastrmcp_app.call_tool("   ", {"x": 1})

        # Test invalid arguments
        with pytest.raises(ValueError, match="Arguments must be a dictionary"):
            await fastrmcp_app.call_tool("test_tool", "not a dict")  # type: ignore

        with pytest.raises(ValueError, match="Arguments must be a dictionary"):
            await fastrmcp_app.call_tool("test_tool", None)  # type: ignore

        # Test invalid idempotency key
        with pytest.raises(ValueError, match="Idempotency key must be a string or None"):
            await fastrmcp_app.call_tool("test_tool", {"x": 1}, idempotency_key=123)  # type: ignore
