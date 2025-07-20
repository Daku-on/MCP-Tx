"""FastRMCP - Decorator-based API for RMCP reliability features.

FastRMCP provides a decorator-based interface similar to FastMCP, allowing developers
to easily add RMCP reliability features (retry, idempotency, ACK/NACK) to their tools.
"""

from __future__ import annotations

import copy
import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import anyio

from rmcp.session import RMCPSession
from rmcp.types import RetryPolicy, RMCPConfig, RMCPResult

logger = logging.getLogger(__name__)

# Type aliases
AnyFunction = TypeVar("AnyFunction", bound=Callable[..., Any])
SyncFunction = Callable[..., Any]
AsyncFunction = Callable[..., Awaitable[Any]]


class ToolRegistry:
    """Registry for managing registered tools."""

    def __init__(self, max_tools: int = 1000) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._max_tools = max_tools

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        retry_policy: RetryPolicy | None = None,
        idempotency_key_generator: Callable[[dict[str, Any]], str] | None = None,
        timeout_ms: int | None = None,
        description: str | None = None,
    ) -> None:
        """Register a tool with the registry."""
        if len(self._tools) >= self._max_tools:
            raise ValueError(f"Registry full: cannot register more than {self._max_tools} tools")

        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")

        self._tools[name] = {
            "func": func,
            "retry_policy": retry_policy,
            "idempotency_key_generator": idempotency_key_generator,
            "timeout_ms": timeout_ms,
            "description": description or func.__doc__,
            "is_async": inspect.iscoroutinefunction(func),
        }
        logger.debug(f"Registered tool: {name}")

    def get_tool(self, name: str) -> dict[str, Any] | None:
        """Get tool configuration by name.

        Returns a deep copy to prevent mutation of cached tool configurations.
        """
        tool = self._tools.get(name)
        return copy.deepcopy(tool) if tool is not None else None

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> dict[str, Any] | None:
        """Get tool metadata for introspection."""
        tool = self._tools.get(name)
        if not tool:
            return None

        return {
            "name": name,
            "description": tool["description"],
            "is_async": tool["is_async"],
            "has_retry_policy": tool["retry_policy"] is not None,
            "timeout_ms": tool["timeout_ms"],
        }

    def get_all_tools_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered tools efficiently."""
        return {
            name: {
                "name": name,
                "description": tool["description"],
                "is_async": tool["is_async"],
                "has_retry_policy": tool["retry_policy"] is not None,
                "timeout_ms": tool["timeout_ms"],
            }
            for name, tool in self._tools.items()
        }


class FastRMCP:
    """FastRMCP - Decorator-based RMCP reliability for MCP tools.

    FastRMCP wraps an existing MCP session and provides a decorator-based interface
    for adding RMCP reliability features to tool functions. Tools registered with
    FastRMCP automatically get retry logic, idempotency, and ACK/NACK handling.

    Example:
        ```python
        from rmcp import FastRMCP, RetryPolicy

        # Wrap existing MCP session
        app = FastRMCP(mcp_session)

        @app.tool()
        async def my_tool(arg: str) -> str:
            \"\"\"A reliable tool with automatic retry.\"\"\"
            return f"Result: {arg}"

        @app.tool(retry_policy=RetryPolicy(max_attempts=5))
        async def critical_tool(data: dict) -> dict:
            \"\"\"Critical tool with custom retry policy.\"\"\"
            return {"processed": data}

        # Call tools with automatic RMCP reliability
        result = await app.call_tool("my_tool", {"arg": "test"})
        ```
    """

    def __init__(
        self,
        mcp_session: Any,
        config: RMCPConfig | None = None,
        name: str = "FastRMCP App",
        max_tools: int = 1000,
    ) -> None:
        """Initialize FastRMCP with an MCP session.

        Args:
            mcp_session: An existing MCP session to wrap
            config: Optional RMCP configuration
            name: Application name for logging and debugging
            max_tools: Maximum number of tools that can be registered
        """
        self.name = name
        self._mcp_session = mcp_session
        self._rmcp_session: RMCPSession | None = None
        self._config = config or RMCPConfig()
        self._registry = ToolRegistry(max_tools=max_tools)
        self._initialized = False
        self._init_lock = anyio.Lock()

        logger.info(f"Created FastRMCP app: {name}")

    async def initialize(self) -> None:
        """Initialize the RMCP session."""
        # Fast path: check if already initialized without acquiring lock
        if self._initialized:
            return

        # Double-check pattern: verify state after acquiring lock
        async with self._init_lock:
            if self._initialized:
                return

            self._rmcp_session = RMCPSession(self._mcp_session, self._config)
            await self._rmcp_session.initialize()
            self._initialized = True
            logger.info(f"Initialized FastRMCP app: {self.name}")

    async def __aenter__(self) -> FastRMCP:
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._rmcp_session:
            await self._rmcp_session.__aexit__(exc_type, exc_val, exc_tb)
        logger.info(f"Closed FastRMCP app: {self.name}")

    def tool(
        self,
        name: str | None = None,
        retry_policy: RetryPolicy | None = None,
        idempotency_key_generator: Callable[[dict[str, Any]], str] | None = None,
        timeout_ms: int | None = None,
        description: str | None = None,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """Decorator to register a tool with RMCP reliability features.

        The decorated function will automatically get RMCP reliability features:
        - Automatic retry with exponential backoff
        - Request deduplication and idempotency
        - ACK/NACK message handling
        - Timeout protection

        Args:
            name: Tool name (defaults to function name)
            retry_policy: Custom retry policy for this tool
            idempotency_key_generator: Custom function to generate idempotency keys
            timeout_ms: Tool-specific timeout in milliseconds
            description: Tool description (defaults to function docstring)

        Example:
            ```python
            @app.tool()
            def simple_tool(x: int) -> str:
                return str(x)

            @app.tool(
                retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=2000),
                timeout_ms=30000
            )
            async def critical_tool(data: dict) -> dict:
                # Critical operation with aggressive retry
                return process_data(data)
            ```
        """
        # Handle case where decorator is used without parentheses
        if callable(name):
            raise TypeError("The @tool decorator requires parentheses. Use @tool() instead of @tool")

        def decorator(func: AnyFunction) -> AnyFunction:
            tool_name = name or func.__name__

            # Register the tool
            self._registry.register_tool(
                name=tool_name,
                func=func,
                retry_policy=retry_policy,
                idempotency_key_generator=idempotency_key_generator,
                timeout_ms=timeout_ms,
                description=description,
            )

            # Return the original function unchanged
            return func

        return decorator

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> RMCPResult:
        """Call a registered tool with RMCP reliability features.

        Args:
            name: Name of the registered tool
            arguments: Tool arguments
            idempotency_key: Optional custom idempotency key

        Returns:
            RMCPResult with tool execution result and reliability metadata

        Raises:
            ValueError: If tool is not registered or arguments are invalid
            RuntimeError: If FastRMCP is not initialized
        """
        # Input validation
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a non-empty string")

        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")

        if idempotency_key is not None and not isinstance(idempotency_key, str):
            raise ValueError("Idempotency key must be a string or None")

        if not self._initialized or not self._rmcp_session:
            raise RuntimeError("FastRMCP not initialized. Use 'async with app:' or call 'await app.initialize()'")

        tool_config = self._registry.get_tool(name)
        if not tool_config:
            raise ValueError(f"Tool '{name}' not registered. Available tools: {self._registry.list_tools()}")

        # Generate idempotency key if needed
        if idempotency_key is None and tool_config["idempotency_key_generator"]:
            try:
                idempotency_key = tool_config["idempotency_key_generator"](arguments)
            except Exception as e:
                logger.warning(f"Failed to generate idempotency key for tool '{name}': {e}")

        # Call tool through RMCP session with configured policies
        return await self._rmcp_session.call_tool(
            name=name,
            arguments=arguments,
            retry_policy=tool_config["retry_policy"],
            timeout_ms=tool_config["timeout_ms"],
            idempotency_key=idempotency_key,
        )

    def list_tools(self) -> list[str]:
        """List all registered tools."""
        return self._registry.list_tools()

    def get_tool_info(self, name: str) -> dict[str, Any] | None:
        """Get information about a registered tool."""
        return self._registry.get_tool_info(name)

    def get_all_tools_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all registered tools."""
        return self._registry.get_all_tools_info()


# Convenience exports
__all__ = ["FastRMCP", "ToolRegistry"]
