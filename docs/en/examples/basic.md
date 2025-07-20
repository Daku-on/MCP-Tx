# Basic Usage Examples

Practical examples of common MCP-Tx usage patterns.

## Simple Tool Calls

### Basic File Operations

```python
import asyncio
from mcp_tx import MCPTxSession

async def file_operations_example():
    """Basic file operations with MCP-Tx reliability."""
    
    # Assume mcp_session is your configured MCP session
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # Read a file
        result = await rmcp.call_tool(
            "file_reader",
            {"path": "/path/to/data.txt"}
        )
        
        if result.ack:
            content = result.result.get("content", "")
            print(f"File content: {content}")
        else:
            print(f"Failed to read file: {result.rmcp_meta.error_message}")
        
        # Write a file with idempotency
        result = await rmcp.call_tool(
            "file_writer",
            {
                "path": "/path/to/output.txt",
                "content": "Hello, MCP-Tx!"
            },
            idempotency_key="write-hello-2024-01-15"
        )
        
        print(f"Write successful: {result.ack}")
        print(f"Attempts needed: {result.attempts}")

asyncio.run(file_operations_example())
```

### API Calls with Reliability

```python
import asyncio
import os
from mcp_tx import MCPTxSession, RetryPolicy

async def api_calls_example():
    """API calls with custom retry policies."""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # API call with aggressive retry for critical operations
        critical_retry = RetryPolicy(
            max_attempts=5,
            base_delay_ms=1000,
            backoff_multiplier=1.5,
            jitter=True
        )
        
        result = await rmcp.call_tool(
            "http_client",
            {
                "method": "GET",
                "url": "https://api.example.com/critical-data",
                "headers": {"Authorization": f"Bearer {os.environ['API_TOKEN']}"}}
            },
            retry_policy=critical_retry,
            timeout_ms=30000
        )
        
        if result.ack:
            api_data = result.result
            print(f"API response: {api_data}")
            print(f"Required {result.attempts} attempts")
        else:
            print(f"API call failed after {result.attempts} attempts")
            print(f"Error: {result.rmcp_meta.error_message}")

asyncio.run(api_calls_example())
```

## Error Handling Patterns

### Graceful Error Recovery

```python
import asyncio
import logging
from mcp_tx import MCPTxSession
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError

async def error_handling_example():
    """Demonstrates robust error handling patterns."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # Example 1: Timeout handling with fallback
        try:
            result = await rmcp.call_tool(
                "slow_operation",
                {"data_size": "large"},
                timeout_ms=5000  # 5 second timeout
            )
            
            if result.ack:
                logger.info("Operation completed successfully")
                return result.result
                
        except MCP-TxTimeoutError as e:
            logger.warning(f"Operation timed out: {e.message}")
            
            # Fallback: Try with longer timeout
            try:
                result = await rmcp.call_tool(
                    "slow_operation",
                    {"data_size": "small"},  # Smaller dataset
                    timeout_ms=15000  # Longer timeout
                )
                logger.info("Fallback operation succeeded")
                return result.result
                
            except MCP-TxTimeoutError:
                logger.error("Even fallback operation timed out")
                return None
        
        # Example 2: Network error handling
        try:
            result = await rmcp.call_tool("external_api", {"endpoint": "/data"})
            
        except MCP-TxNetworkError as e:
            logger.warning(f"Network error: {e.message}")
            
            # Wait and retry once
            await asyncio.sleep(2)
            
            try:
                result = await rmcp.call_tool("external_api", {"endpoint": "/data"})
                logger.info("Retry succeeded after network error")
                
            except MCP-TxNetworkError:
                logger.error("Network still unavailable after retry")
                return None

asyncio.run(error_handling_example())
```

### Validation and Input Sanitization

```python
import asyncio
from mcp_tx import MCPTxSession

async def validation_example():
    """Input validation and sanitization patterns."""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        def validate_file_path(path: str) -> str:
            """Validate and sanitize file paths."""
            if not path or not path.strip():
                raise ValueError("File path cannot be empty")
            
            # Remove potential directory traversal
            import os.path
            path = os.path.normpath(os.path.abspath(path))
            
            # Ensure path is within safe directory
            safe_base = "/safe_directory"
            if not path.startswith(safe_base):
                raise ValueError(f"Path must be within {safe_base}")
            
            # Ensure absolute path
            if not path.startswith("/"):
                path = f"/safe_directory/{path}"
            
            return path
        
        def create_idempotency_key(operation: str, params: dict) -> str:
            """Create unique, descriptive idempotency keys."""
            import hashlib
            import json
            from datetime import datetime
            
            # Create deterministic hash from parameters
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
            
            # Include timestamp for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d")
            
            return f"{operation}-{params_hash}-{timestamp}"
        
        # Example: Safe file operation
        try:
            file_path = validate_file_path("../../../etc/passwd")  # Malicious input
            
            result = await rmcp.call_tool(
                "file_reader",
                {"path": file_path},
                idempotency_key=create_idempotency_key("read", {"path": file_path})
            )
            
            if result.ack:
                print(f"Safely read file: {file_path}")
            
        except ValueError as e:
            print(f"Invalid input: {e}")
        
        # Example: Parameter validation
        def validate_api_params(params: dict) -> dict:
            """Validate API parameters."""
            required_fields = ["endpoint", "method"]
            
            for field in required_fields:
                if field not in params:
                    raise ValueError(f"Missing required field: {field}")
            
            # Sanitize method
            method = params["method"].upper()
            if method not in ["GET", "POST", "PUT", "DELETE"]:
                raise ValueError(f"Invalid HTTP method: {method}")
            params["method"] = method
            
            return params
        
        try:
            api_params = validate_api_params({
                "endpoint": "/users",
                "method": "get",  # Will be normalized to GET
                "data": {"name": "Alice"}
            })
            
            result = await rmcp.call_tool("http_client", api_params)
            
        except ValueError as e:
            print(f"Invalid API parameters: {e}")

asyncio.run(validation_example())
```

## Concurrency Patterns

### Parallel Tool Execution

```python
import asyncio
from mcp_tx import MCPTxSession

async def parallel_execution_example():
    """Execute multiple tools concurrently with MCP-Tx."""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # Example 1: Independent parallel operations
        async def process_file(file_path: str) -> dict:
            """Process a single file."""
            return await rmcp.call_tool(
                "file_processor",
                {"path": file_path, "operation": "analyze"},
                idempotency_key=f"analyze-{file_path.replace('/', '_')}"
            )
        
        # Process multiple files in parallel
        file_paths = ["/data/file1.txt", "/data/file2.txt", "/data/file3.txt"]
        
        tasks = [process_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"File {file_paths[i]} failed: {result}")
            elif result.ack:
                successful_results.append(result.result)
                print(f"File {file_paths[i]} processed successfully")
            else:
                print(f"File {file_paths[i]} processing failed")
        
        print(f"Successfully processed {len(successful_results)} files")
        
        # Example 2: Producer-consumer pattern
        async def producer(queue: asyncio.Queue):
            """Produce work items."""
            for i in range(10):
                await queue.put(f"task_{i}")
            await queue.put(None)  # Sentinel
        
        async def consumer(queue: asyncio.Queue, consumer_id: int):
            """Consume and process work items."""
            processed = 0
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break
                
                try:
                    result = await rmcp.call_tool(
                        "work_processor",
                        {"task": item, "worker_id": consumer_id}
                    )
                    
                    if result.ack:
                        processed += 1
                        print(f"Consumer {consumer_id} processed {item}")
                    
                except Exception as e:
                    print(f"Consumer {consumer_id} failed on {item}: {e}")
                
                finally:
                    queue.task_done()
            
            return processed
        
        # Run producer-consumer pattern
        work_queue = asyncio.Queue(maxsize=20)
        
        # Start producer and consumers
        producer_task = asyncio.create_task(producer(work_queue))
        consumer_tasks = [
            asyncio.create_task(consumer(work_queue, i)) 
            for i in range(3)
        ]
        
        # Wait for completion
        await producer_task
        await work_queue.join()
        
        # Get consumer results
        consumer_results = await asyncio.gather(*consumer_tasks)
        total_processed = sum(consumer_results)
        print(f"Total items processed: {total_processed}")

asyncio.run(parallel_execution_example())
```

### Rate-Limited Operations

```python
import asyncio
from mcp_tx import MCPTxSession

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_call
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_call = asyncio.get_event_loop().time()

async def rate_limited_example():
    """Rate-limited API calls with MCP-Tx."""
    
    # Limit to 2 calls per second
    rate_limiter = RateLimiter(calls_per_second=2.0)
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        async def rate_limited_api_call(endpoint: str) -> dict:
            """Make rate-limited API call."""
            await rate_limiter.acquire()
            
            return await rmcp.call_tool(
                "api_client",
                {"endpoint": endpoint},
                idempotency_key=f"api-{endpoint.replace('/', '_')}"
            )
        
        # Make multiple API calls respecting rate limit
        endpoints = [f"/users/{i}" for i in range(1, 11)]
        
        start_time = asyncio.get_event_loop().time()
        
        tasks = [rate_limited_api_call(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        
        successful_calls = sum(1 for result in results if result.ack)
        print(f"Completed {successful_calls} API calls in {end_time - start_time:.2f} seconds")

asyncio.run(rate_limited_example())
```

## Configuration Examples

### Environment-Specific Configuration

```python
import os
from mcp_tx import MCPTxSession, MCPTxConfig, RetryPolicy

def create_rmcp_config() -> MCPTxConfig:
    """Create environment-specific MCP-Tx configuration."""
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        return MCPTxConfig(
            default_timeout_ms=30000,  # 30 seconds
            retry_policy=RetryPolicy(
                max_attempts=5,
                base_delay_ms=2000,     # 2 seconds
                backoff_multiplier=2.0,
                jitter=True
            ),
            max_concurrent_requests=20,
            deduplication_window_ms=600000,  # 10 minutes
            enable_transactions=True,
            enable_monitoring=True
        )
    
    elif environment == "staging":
        return MCPTxConfig(
            default_timeout_ms=15000,  # 15 seconds
            retry_policy=RetryPolicy(
                max_attempts=3,
                base_delay_ms=1000,     # 1 second
                backoff_multiplier=1.5,
                jitter=True
            ),
            max_concurrent_requests=10,
            deduplication_window_ms=300000,  # 5 minutes
        )
    
    else:  # development
        return MCPTxConfig(
            default_timeout_ms=5000,   # 5 seconds
            retry_policy=RetryPolicy(
                max_attempts=2,
                base_delay_ms=500,      # 0.5 seconds
                backoff_multiplier=1.0, # No backoff for fast dev cycles
                jitter=False
            ),
            max_concurrent_requests=5,
            deduplication_window_ms=60000,   # 1 minute
        )

async def environment_config_example():
    """Use environment-specific configuration."""
    
    config = create_rmcp_config()
    
    async with MCPTxSession(mcp_session, config) as rmcp:
        await rmcp.initialize()
        
        print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        print(f"Max concurrent requests: {config.max_concurrent_requests}")
        print(f"Default timeout: {config.default_timeout_ms}ms")
        print(f"Max retry attempts: {config.retry_policy.max_attempts}")
        
        # Use the configured session
        result = await rmcp.call_tool("test_tool", {})
        print(f"Test successful: {result.ack}")
```

---

**Next**: [Migration Guide](../migration.md) →