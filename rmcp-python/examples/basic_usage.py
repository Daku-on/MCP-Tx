"""
Basic RMCP usage example.

This example shows how to wrap an existing MCP session with RMCP
to add reliability features like ACK/NACK, retry, and deduplication.
"""

import asyncio
import logging
from typing import Any, ClassVar

from rmcp import RetryPolicy, RMCPConfig, RMCPSession


class MockMCPSession:
    """
    Mock MCP session for demonstration purposes.
    In real usage, this would be your actual MCP client session.
    """

    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self.call_count = 0

    async def initialize(self, **kwargs) -> Any:
        """Mock initialization with RMCP capability support."""
        print("🔌 Initializing MCP session...")

        # Mock server response with RMCP support
        class MockCapabilities:
            experimental: ClassVar[dict[str, Any]] = {
                "rmcp": {"version": "0.1.0", "features": ["ack", "retry", "idempotency"]}
            }

        class MockResult:
            capabilities = MockCapabilities()

        return MockResult()

    async def send_request(self, request: dict[str, Any]) -> Any:
        """Mock tool execution."""
        self.call_count += 1

        tool_name = request.get("params", {}).get("name", "unknown")
        print(f"🔧 Executing tool: {tool_name} (attempt #{self.call_count})")

        # Simulate random failures
        import random

        if random.random() < self.failure_rate:
            raise Exception(f"Simulated network error for {tool_name}")

        # Simulate processing delay
        await asyncio.sleep(0.1)

        return {
            "result": {
                "content": [{"type": "text", "text": f"Tool {tool_name} executed successfully! Data processed."}]
            }
        }


async def basic_example():
    """Demonstrate basic RMCP usage."""
    print("🚀 RMCP Basic Usage Example")
    print("=" * 40)

    # Create mock MCP session (in real usage, this would be your actual MCP session)
    mcp_session = MockMCPSession(failure_rate=0.3)  # 30% failure rate for demo

    # Configure RMCP with custom settings
    config = RMCPConfig(
        default_timeout_ms=5000,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=500, backoff_multiplier=1.5, jitter=True),
        max_concurrent_requests=5,
    )

    # Wrap MCP session with RMCP
    rmcp_session = RMCPSession(mcp_session, config)

    try:
        # Initialize session with capability negotiation
        print("\n📋 Initializing RMCP session...")
        await rmcp_session.initialize()

        if rmcp_session.rmcp_enabled:
            print("✅ RMCP enabled - reliability features active")
        else:
            print("⚠️  RMCP disabled - falling back to standard MCP")

        print("\n🎯 Running tool call examples...")

        # Example 1: Simple tool call
        print("\n1️⃣ Simple tool call:")
        result1 = await rmcp_session.call_tool("file_reader", {"path": "/tmp/data.json"})
        print(f"   ✅ ACK: {result1.ack}")
        print(f"   ✅ Processed: {result1.processed}")
        print(f"   🔁 Attempts: {result1.attempts}")
        print(f"   📊 Status: {result1.final_status}")

        # Example 2: Tool call with idempotency
        print("\n2️⃣ Tool call with idempotency (prevents duplicates):")
        idempotency_key = "write_config_v1"

        result2a = await rmcp_session.call_tool(
            "file_writer",
            {"path": "/config/settings.json", "content": '{"mode": "production"}'},
            idempotency_key=idempotency_key,
        )
        print(f"   First call - Duplicate: {result2a.rmcp_meta.duplicate}")

        # Same call again - should be deduplicated
        result2b = await rmcp_session.call_tool(
            "file_writer",
            {"path": "/config/settings.json", "content": '{"mode": "staging"}'},  # Different content!
            idempotency_key=idempotency_key,  # Same key
        )
        print(f"   Second call - Duplicate: {result2b.rmcp_meta.duplicate}")

        # Example 3: Tool call with custom timeout and retry
        print("\n3️⃣ Tool call with custom retry policy:")
        custom_retry = RetryPolicy(max_attempts=5, base_delay_ms=200, backoff_multiplier=2.0)

        result3 = await rmcp_session.call_tool(
            "api_caller",
            {"url": "https://api.example.com/data", "method": "GET"},
            timeout_ms=3000,
            retry_policy=custom_retry,
        )
        print(f"   🔁 Total attempts: {result3.attempts}")
        print(f"   📊 Final status: {result3.final_status}")

        # Example 4: Concurrent tool calls
        print("\n4️⃣ Concurrent tool calls:")
        tasks = []
        for i in range(3):
            task = rmcp_session.call_tool(f"processor_{i}", {"data": f"batch_{i}", "index": i})
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            print(f"   Task {i}: ✅ Success={result.ack}, Attempts={result.attempts}")

        # Show active requests (should be empty now)
        active = rmcp_session.active_requests
        print(f"\n📈 Active requests: {len(active)}")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        # Clean up
        print("\n🧹 Closing RMCP session...")
        await rmcp_session.close()
        print("✅ Session closed successfully")


async def retry_demonstration():
    """Demonstrate retry behavior with failures."""
    print("\n" + "=" * 40)
    print("🔄 RMCP Retry Demonstration")
    print("=" * 40)

    # Create MCP session with high failure rate
    mcp_session = MockMCPSession(failure_rate=0.7)  # 70% failure rate

    # Configure aggressive retry policy
    config = RMCPConfig(
        retry_policy=RetryPolicy(
            max_attempts=5,
            base_delay_ms=100,
            backoff_multiplier=1.2,
            jitter=False,  # Disable jitter for predictable demo
        )
    )

    rmcp_session = RMCPSession(mcp_session, config)

    try:
        await rmcp_session.initialize()
        print(f"🎯 Calling unreliable tool with {config.retry_policy.max_attempts} max attempts...")

        result = await rmcp_session.call_tool("unreliable_tool", {"operation": "risky_operation"})

        if result.ack:
            print(f"✅ Success after {result.attempts} attempts!")
            print(f"📊 Final status: {result.final_status}")
        else:
            print(f"❌ Failed after {result.attempts} attempts")
            print(f"🚨 Error: {result.rmcp_meta.error_message}")

    finally:
        await rmcp_session.close()


async def main():
    """Run all examples."""
    # Set up logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    try:
        await basic_example()
        await retry_demonstration()

        print("\n🎉 All examples completed!")
        print("\nKey RMCP features demonstrated:")
        print("  ✅ ACK/NACK guarantees")
        print("  🔁 Automatic retry with exponential backoff")
        print("  🔒 Request deduplication via idempotency keys")
        print("  ⚡ Concurrent request handling")
        print("  🎛️  Configurable timeouts and retry policies")
        print("  🔄 100% MCP compatibility")

    except KeyboardInterrupt:
        print("\n⏹️  Example interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
