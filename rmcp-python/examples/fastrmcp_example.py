"""FastRMCP Example - Decorator-based RMCP reliability.

This example demonstrates how to use FastRMCP to add RMCP reliability features
to MCP tools using decorators, similar to FastMCP but for client-side reliability.
"""

import asyncio
import os
from datetime import datetime

from rmcp import FastRMCP, RetryPolicy, RMCPConfig


async def main():
    """FastRMCP example with decorator-based tool registration."""
    
    # Create a mock MCP session for demonstration
    # In real usage, you would connect to an actual MCP server
    class MockMCPSession:
        """Mock MCP session for demonstration."""
        
        async def initialize(self, **kwargs):
            """Mock initialization."""
            pass
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Mock context manager exit."""
            pass
        
        async def call_tool(self, name: str, arguments: dict) -> dict:
            """Simulate tool calls."""
            print(f"🔧 Calling MCP tool: {name} with {arguments}")
            
            # Simulate different responses based on tool name
            if name == "unreliable_api":
                # Sometimes fail to demonstrate retry
                import random
                if random.random() < 0.3:  # 30% failure rate
                    raise Exception("Simulated network error")
                return {"status": "success", "data": f"API result for {arguments}"}
            
            elif name == "file_processor":
                filename = arguments.get("filename", "unknown")
                return {
                    "processed": True,
                    "filename": filename,
                    "size": len(filename) * 100,  # Mock file size
                    "timestamp": datetime.now().isoformat()
                }
            
            elif name == "database_query":
                query = arguments.get("query", "")
                return {
                    "rows": [
                        {"id": 1, "name": "Alice", "query": query},
                        {"id": 2, "name": "Bob", "query": query}
                    ],
                    "count": 2
                }
            
            else:
                return {"echo": arguments}
    
    # Create mock MCP session
    mcp_session = MockMCPSession()
    
    # Create FastRMCP app with custom configuration
    config = RMCPConfig(
        default_timeout_ms=10000,  # 10 second default timeout
        max_concurrent_requests=5,
        deduplication_window_ms=300000,  # 5 minute deduplication window
    )
    
    app = FastRMCP(mcp_session, config=config, name="Example RMCP App")
    
    # Register tools with decorators
    
    @app.tool()
    async def simple_echo(message: str) -> str:
        """Simple echo tool with default RMCP reliability."""
        # This tool gets automatic retry, idempotency, and ACK/NACK handling
        return f"Echo: {message}"
    
    @app.tool(
        retry_policy=RetryPolicy(
            max_attempts=5,
            base_delay_ms=1000,  # 1 second base delay
            backoff_multiplier=2.0,
            jitter=True
        ),
        timeout_ms=30000  # 30 second timeout for this tool
    )
    async def unreliable_api(endpoint: str, data: dict) -> dict:
        """API call with aggressive retry policy."""
        # This tool will retry up to 5 times with exponential backoff
        return {"endpoint": endpoint, "data": data}
    
    @app.tool(
        retry_policy=RetryPolicy(max_attempts=2),  # Quick retry for file operations
        idempotency_key_generator=lambda args: f"file-{args['filename']}-{args.get('operation', 'process')}"
    )
    async def file_processor(filename: str, operation: str = "process") -> dict:
        """File processing tool with custom idempotency."""
        # Custom idempotency key ensures same file+operation isn't processed twice
        return {"filename": filename, "operation": operation}
    
    @app.tool(
        name="db_query",  # Custom tool name
        timeout_ms=15000,  # 15 second timeout for database operations
        description="Execute database query with connection retry"
    )
    async def database_query(query: str, params: dict = None) -> dict:
        """Database query tool with connection reliability."""
        return {"query": query, "params": params or {}}
    
    # Initialize and use the FastRMCP app
    async with app:
        print(f"🚀 Started {app.name}")
        print(f"📋 Registered tools: {app.list_tools()}")
        print()
        
        # Display tool information
        print("🔍 Tool Information:")
        for tool_name in app.list_tools():
            info = app.get_tool_info(tool_name)
            print(f"  • {tool_name}: {info['description']}")
            print(f"    - Async: {info['is_async']}")
            print(f"    - Has retry policy: {info['has_retry_policy']}")
            print(f"    - Timeout: {info['timeout_ms']}ms")
            print()
        
        # Example 1: Simple tool call
        print("📞 Example 1: Simple echo tool")
        try:
            result = await app.call_tool("simple_echo", {"message": "Hello, RMCP!"})
            print(f"  ✅ Result: {result.result}")
            print(f"  📊 Attempts: {result.rmcp_meta.attempts}")
            print(f"  🔄 Duplicate: {result.rmcp_meta.duplicate}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()
        
        # Example 2: Unreliable API with retry
        print("📞 Example 2: Unreliable API (with retry)")
        try:
            result = await app.call_tool("unreliable_api", {
                "endpoint": "/users",
                "data": {"filter": "active"}
            })
            print(f"  ✅ Result: {result.result}")
            print(f"  📊 Attempts: {result.rmcp_meta.attempts}")
            print(f"  ⏱️  Final status: {result.rmcp_meta.final_status}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()
        
        # Example 3: File processing with idempotency
        print("📞 Example 3: File processing (with idempotency)")
        filename = "important_data.csv"
        
        # Call the same operation twice
        for i in range(2):
            try:
                result = await app.call_tool("file_processor", {
                    "filename": filename,
                    "operation": "backup"
                })
                print(f"  Call {i+1}:")
                print(f"    ✅ Result: {result.result}")
                print(f"    🔄 Duplicate: {result.rmcp_meta.duplicate}")
                print(f"    📊 Attempts: {result.rmcp_meta.attempts}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        print()
        
        # Example 4: Database query with custom timeout
        print("📞 Example 4: Database query (custom timeout)")
        try:
            result = await app.call_tool("db_query", {
                "query": "SELECT * FROM users WHERE active = ?",
                "params": {"active": True}
            })
            print(f"  ✅ Result: {result.result}")
            print(f"  📊 Attempts: {result.rmcp_meta.attempts}")
            print(f"  ✅ ACK received: {result.rmcp_meta.ack}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()
        
        # Example 5: Parallel tool execution
        print("📞 Example 5: Parallel tool execution")
        tasks = []
        for i in range(3):
            tasks.extend([
                app.call_tool("simple_echo", {"message": f"Message {i}"}),
                app.call_tool("file_processor", {"filename": f"file_{i}.txt"}),
                app.call_tool("db_query", {"query": f"SELECT * FROM table_{i}"})
            ])
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Task {i}: ❌ {result}")
                else:
                    print(f"  Task {i}: ✅ Attempts: {result.rmcp_meta.attempts}, ACK: {result.rmcp_meta.ack}")
        except Exception as e:
            print(f"  ❌ Parallel execution error: {e}")
        
        print("\n🎉 FastRMCP example completed!")


if __name__ == "__main__":
    asyncio.run(main())