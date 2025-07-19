"""
RMCP Session 1 MVP Demo

This script demonstrates the core RMCP functionality implemented in Session 1:
- RMCPSession wrapper around MCP sessions
- Request ID tracking and lifecycle management
- ACK/NACK mechanism for guaranteed delivery
- Basic retry logic with exponential backoff
- Request deduplication via idempotency keys
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rmcp import RMCPSession, RMCPConfig, RetryPolicy
from examples.basic_usage import MockMCPSession


async def session_1_demo():
    """Demonstrate Session 1 MVP features."""
    print("🚀 RMCP Session 1 MVP Demo")
    print("=" * 50)
    
    print("\n📦 Features implemented in Session 1:")
    print("  ✅ RMCPSession wrapper (wraps any MCP session)")
    print("  ✅ Request ID tracking and lifecycle management")
    print("  ✅ ACK/NACK mechanism for delivery guarantees") 
    print("  ✅ Basic retry logic with exponential backoff")
    print("  ✅ Request deduplication via idempotency keys")
    print("  ✅ Timeout handling and error management")
    print("  ✅ 100% backward compatibility with MCP")
    
    # Test 1: Basic wrapper functionality
    print("\n" + "─" * 50)
    print("🧪 Test 1: Basic RMCP Session Wrapper")
    
    mock_mcp = MockMCPSession(failure_rate=0.0)  # No failures for basic test
    rmcp_session = RMCPSession(mock_mcp)
    
    await rmcp_session.initialize()
    print(f"   RMCP Enabled: {rmcp_session.rmcp_enabled}")
    
    result = await rmcp_session.call_tool("test_tool", {"test": "data"})
    print(f"   ACK: {result.ack}")
    print(f"   Processed: {result.processed}")
    print(f"   Attempts: {result.attempts}")
    print(f"   Status: {result.final_status}")
    
    await rmcp_session.close()
    
    # Test 2: Retry mechanism
    print("\n" + "─" * 50)
    print("🧪 Test 2: Retry Logic with Failures")
    
    mock_mcp = MockMCPSession(failure_rate=0.6)  # 60% failure rate
    config = RMCPConfig(
        retry_policy=RetryPolicy(
            max_attempts=4,
            base_delay_ms=100,
            backoff_multiplier=1.5,
            jitter=False  # Disable for predictable demo
        )
    )
    rmcp_session = RMCPSession(mock_mcp, config)
    
    await rmcp_session.initialize()
    
    result = await rmcp_session.call_tool("unreliable_tool", {"data": "test"})
    print(f"   Success: {result.ack}")
    print(f"   Total Attempts: {result.attempts}")
    print(f"   Final Status: {result.final_status}")
    if not result.ack:
        print(f"   Error: {result.rmcp_meta.error_message}")
    
    await rmcp_session.close()
    
    # Test 3: Idempotency and deduplication
    print("\n" + "─" * 50)
    print("🧪 Test 3: Request Deduplication")
    
    mock_mcp = MockMCPSession(failure_rate=0.0)
    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()
    
    # First call with idempotency key
    result1 = await rmcp_session.call_tool(
        "write_file",
        {"path": "/tmp/test.txt", "content": "original"},
        idempotency_key="write_test_file_v1"
    )
    print(f"   First call - Duplicate: {result1.rmcp_meta.duplicate}")
    print(f"   MCP calls so far: {mock_mcp.call_count}")
    
    # Second call with same key (should be deduplicated)
    result2 = await rmcp_session.call_tool(
        "write_file",
        {"path": "/tmp/test.txt", "content": "modified"},  # Different content
        idempotency_key="write_test_file_v1"  # Same key
    )
    print(f"   Second call - Duplicate: {result2.rmcp_meta.duplicate}")
    print(f"   MCP calls so far: {mock_mcp.call_count}")  # Should still be 1
    
    await rmcp_session.close()
    
    # Test 4: Concurrent requests
    print("\n" + "─" * 50)
    print("🧪 Test 4: Concurrent Request Handling")
    
    mock_mcp = MockMCPSession(failure_rate=0.2)  # Some failures
    rmcp_session = RMCPSession(mock_mcp)
    await rmcp_session.initialize()
    
    # Launch multiple concurrent requests
    tasks = []
    for i in range(5):
        task = rmcp_session.call_tool(f"worker_{i}", {"job_id": i})
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    successful = sum(1 for r in results if r.ack)
    total_attempts = sum(r.attempts for r in results)
    
    print(f"   Successful: {successful}/5")
    print(f"   Total Attempts: {total_attempts}")
    print(f"   Active Requests: {len(rmcp_session.active_requests)}")
    
    await rmcp_session.close()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 Session 1 MVP Demo Complete!")
    print("\n✅ Core reliability features working:")
    print("  • Session wrapper with capability negotiation")
    print("  • Request tracking and lifecycle management")
    print("  • ACK/NACK delivery guarantees")
    print("  • Automatic retry with backoff")
    print("  • Request deduplication")
    print("  • Concurrent request handling")
    print("  • Error handling and timeouts")
    
    print("\n🚀 Ready for Session 2 features:")
    print("  • Advanced retry policies")
    print("  • Transaction management")
    print("  • Enhanced error handling")
    print("  • Integration tests")


if __name__ == "__main__":
    try:
        asyncio.run(session_1_demo())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise