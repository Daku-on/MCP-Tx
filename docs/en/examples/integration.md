# RMCP Integration Guide

This guide shows how to integrate RMCP with existing MCP servers and popular frameworks.

## Integrating with Existing MCP Servers

### Basic MCP Server Integration

```python
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioTransport
from rmcp import FastRMCP, RMCPConfig
import asyncio

async def connect_to_mcp_server():
    """Connect to an existing MCP server with RMCP reliability."""
    
    # Connect to standard MCP server
    transport = StdioTransport(
        command=["python", "-m", "mcp_server"],
        cwd="/path/to/server"
    )
    
    async with ClientSession(transport) as mcp_session:
        # Wrap with RMCP
        config = RMCPConfig(
            default_timeout_ms=30000,
            enable_request_logging=True
        )
        
        app = FastRMCP(mcp_session, config)
        
        # Register tool wrappers
        @app.tool()
        async def reliable_file_operation(path: str, operation: str) -> dict:
            """Wrap existing file operations with reliability."""
            return await mcp_session.call_tool(
                "file_operation",
                {"path": path, "operation": operation}
            )
        
        # Use with RMCP features
        async with app:
            result = await app.call_tool(
                "reliable_file_operation",
                {"path": "/data/file.txt", "operation": "read"}
            )
            print(f"Operation completed after {result.rmcp_meta.attempts} attempts")
```

### Multiple MCP Server Integration

```python
class MultiServerRMCP:
    """Integrate multiple MCP servers with unified RMCP interface."""
    
    def __init__(self):
        self.servers = {}
        self.apps = {}
    
    async def add_server(self, name: str, transport):
        """Add an MCP server to the pool."""
        session = ClientSession(transport)
        await session.__aenter__()
        
        app = FastRMCP(session, name=f"RMCP-{name}")
        await app.initialize()
        
        self.servers[name] = session
        self.apps[name] = app
        
        return app
    
    async def call_server_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
        **kwargs
    ):
        """Call tool on specific server."""
        if server_name not in self.apps:
            raise ValueError(f"Unknown server: {server_name}")
        
        return await self.apps[server_name].call_tool(
            tool_name,
            arguments,
            **kwargs
        )
    
    async def broadcast_tool(
        self,
        tool_name: str,
        arguments: dict,
        **kwargs
    ):
        """Call same tool on all servers."""
        tasks = [
            app.call_tool(tool_name, arguments, **kwargs)
            for app in self.apps.values()
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

# Usage
multi_server = MultiServerRMCP()

# Add different MCP servers
await multi_server.add_server(
    "filesystem",
    StdioTransport(["python", "-m", "mcp_filesystem_server"])
)
await multi_server.add_server(
    "database",
    StdioTransport(["python", "-m", "mcp_database_server"])
)

# Use specific server
file_result = await multi_server.call_server_tool(
    "filesystem",
    "read_file",
    {"path": "/data/config.json"}
)
```

## Framework Integrations

### Django Integration

```python
# rmcp_django/middleware.py
from django.conf import settings
from rmcp import FastRMCP, RMCPConfig
import asyncio

class RMCPMiddleware:
    """Django middleware for RMCP integration."""
    
    _instance = None
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._setup_rmcp()
    
    def _setup_rmcp(self):
        """Initialize RMCP connection."""
        if not RMCPMiddleware._instance:
            config = RMCPConfig(
                default_timeout_ms=settings.RMCP_TIMEOUT,
                enable_request_logging=settings.DEBUG
            )
            
            # Initialize in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            mcp_session = self._create_mcp_session()
            RMCPMiddleware._instance = FastRMCP(mcp_session, config)
            
            loop.run_until_complete(RMCPMiddleware._instance.initialize())
    
    def __call__(self, request):
        # Attach RMCP to request
        request.rmcp = RMCPMiddleware._instance
        response = self.get_response(request)
        return response

# rmcp_django/views.py
from django.http import JsonResponse
from asgiref.sync import async_to_sync

def process_with_rmcp(request):
    """Django view using RMCP."""
    tool_name = request.POST.get('tool')
    arguments = request.POST.get('arguments', {})
    
    # Execute RMCP call in sync context
    result = async_to_sync(request.rmcp.call_tool)(
        tool_name,
        arguments
    )
    
    return JsonResponse({
        'success': True,
        'result': result.result,
        'attempts': result.rmcp_meta.attempts
    })
```

### Flask Integration

```python
# rmcp_flask/extension.py
from flask import Flask, g
from rmcp import FastRMCP, RMCPConfig
import asyncio
from functools import wraps

class FlaskRMCP:
    """Flask extension for RMCP."""
    
    def __init__(self, app=None):
        self.app = app
        self._rmcp = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize Flask extension."""
        app.config.setdefault('RMCP_TIMEOUT', 30000)
        app.config.setdefault('RMCP_MAX_RETRIES', 3)
        
        # Setup on first request
        app.before_first_request(self._setup_rmcp)
        app.teardown_appcontext(self._teardown_rmcp)
    
    def _setup_rmcp(self):
        """Initialize RMCP connection."""
        config = RMCPConfig(
            default_timeout_ms=self.app.config['RMCP_TIMEOUT'],
            retry_policy=RetryPolicy(
                max_attempts=self.app.config['RMCP_MAX_RETRIES']
            )
        )
        
        # Create session and RMCP
        mcp_session = self._create_mcp_session()
        self._rmcp = FastRMCP(mcp_session, config)
        
        # Initialize in event loop
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._rmcp.initialize())
    
    @property
    def rmcp(self):
        """Get RMCP instance."""
        return self._rmcp

# Usage in Flask app
from flask import Flask, jsonify
from rmcp_flask import FlaskRMCP

app = Flask(__name__)
rmcp_ext = FlaskRMCP(app)

@app.route('/execute/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """Execute RMCP tool."""
    from flask import request
    
    # Run async operation
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(
        rmcp_ext.rmcp.call_tool(tool_name, request.json)
    )
    
    return jsonify({
        'result': result.result,
        'metadata': {
            'attempts': result.rmcp_meta.attempts,
            'request_id': result.rmcp_meta.request_id
        }
    })
```

### Celery Integration

```python
# rmcp_celery/tasks.py
from celery import Celery, Task
from rmcp import FastRMCP, RMCPConfig
import asyncio

app = Celery('rmcp_tasks')

class RMCPTask(Task):
    """Base task with RMCP support."""
    
    _rmcp = None
    
    @property
    def rmcp(self):
        if RMCPTask._rmcp is None:
            # Initialize RMCP
            config = RMCPConfig(
                default_timeout_ms=60000,  # Longer timeout for background tasks
                retry_policy=RetryPolicy(max_attempts=5)
            )
            
            mcp_session = self._create_mcp_session()
            RMCPTask._rmcp = FastRMCP(mcp_session, config)
            
            # Initialize
            loop = asyncio.new_event_loop()
            loop.run_until_complete(RMCPTask._rmcp.initialize())
        
        return RMCPTask._rmcp

@app.task(base=RMCPTask, bind=True)
def process_data_async(self, data_id: str):
    """Celery task using RMCP."""
    # Run in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Download data
        download_result = loop.run_until_complete(
            self.rmcp.call_tool(
                "download_data",
                {"data_id": data_id},
                idempotency_key=f"celery-download-{data_id}"
            )
        )
        
        # Process data
        process_result = loop.run_until_complete(
            self.rmcp.call_tool(
                "process_data",
                {"file_path": download_result.result["path"]},
                idempotency_key=f"celery-process-{data_id}"
            )
        )
        
        return {
            "status": "completed",
            "result": process_result.result,
            "total_attempts": (
                download_result.rmcp_meta.attempts +
                process_result.rmcp_meta.attempts
            )
        }
    
    except Exception as e:
        # Celery will handle retry
        self.retry(exc=e, countdown=60)
```

## Database Integration

### SQLAlchemy Integration

```python
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class RMCPOperation(Base):
    """Track RMCP operations in database."""
    
    __tablename__ = 'rmcp_operations'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(64), unique=True, index=True)
    tool_name = Column(String(128))
    arguments = Column(JSON)
    idempotency_key = Column(String(128), index=True)
    attempts = Column(Integer)
    status = Column(String(32))
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class DatabaseTrackedRMCP:
    """RMCP with database tracking."""
    
    def __init__(self, app: FastRMCP, db_url: str):
        self.app = app
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    async def call_tool_tracked(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ):
        """Call tool with database tracking."""
        session = self.Session()
        
        # Check for existing operation
        idempotency_key = kwargs.get('idempotency_key')
        if idempotency_key:
            existing = session.query(RMCPOperation).filter_by(
                idempotency_key=idempotency_key,
                status='completed'
            ).first()
            
            if existing:
                # Return cached result
                return RMCPResult(
                    result=existing.result,
                    rmcp_meta=RMCPResponse(
                        ack=True,
                        processed=True,
                        duplicate=True,
                        request_id=existing.request_id,
                        attempts=existing.attempts
                    )
                )
        
        # Create operation record
        operation = RMCPOperation(
            tool_name=name,
            arguments=arguments,
            idempotency_key=idempotency_key,
            status='pending'
        )
        session.add(operation)
        session.commit()
        
        try:
            # Execute operation
            result = await self.app.call_tool(name, arguments, **kwargs)
            
            # Update record
            operation.request_id = result.rmcp_meta.request_id
            operation.attempts = result.rmcp_meta.attempts
            operation.status = 'completed'
            operation.result = result.result
            operation.completed_at = datetime.utcnow()
            session.commit()
            
            return result
            
        except Exception as e:
            operation.status = 'failed'
            operation.completed_at = datetime.utcnow()
            session.commit()
            raise
        
        finally:
            session.close()
```

## Message Queue Integration

### RabbitMQ Integration

```python
import aio_pika
import json

class RabbitMQRMCP:
    """RMCP with RabbitMQ for async processing."""
    
    def __init__(self, app: FastRMCP, amqp_url: str):
        self.app = app
        self.amqp_url = amqp_url
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """Connect to RabbitMQ."""
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        
        # Declare queues
        self.request_queue = await self.channel.declare_queue(
            'rmcp_requests',
            durable=True
        )
        self.response_queue = await self.channel.declare_queue(
            'rmcp_responses',
            durable=True
        )
    
    async def enqueue_tool_call(
        self,
        name: str,
        arguments: dict,
        correlation_id: str
    ):
        """Enqueue tool call for async processing."""
        message = {
            'tool_name': name,
            'arguments': arguments,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                correlation_id=correlation_id,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key='rmcp_requests'
        )
    
    async def process_queue(self):
        """Process queued tool calls."""
        async with self.request_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    
                    try:
                        # Execute tool call
                        result = await self.app.call_tool(
                            data['tool_name'],
                            data['arguments']
                        )
                        
                        # Send response
                        response = {
                            'correlation_id': data['correlation_id'],
                            'success': True,
                            'result': result.result,
                            'metadata': {
                                'request_id': result.rmcp_meta.request_id,
                                'attempts': result.rmcp_meta.attempts
                            }
                        }
                        
                    except Exception as e:
                        response = {
                            'correlation_id': data['correlation_id'],
                            'success': False,
                            'error': str(e)
                        }
                    
                    # Publish response
                    await self.channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(response).encode(),
                            correlation_id=data['correlation_id']
                        ),
                        routing_key='rmcp_responses'
                    )
```

## Cloud Provider Integrations

### AWS Lambda Integration

```python
# lambda_handler.py
import json
import asyncio
from rmcp import FastRMCP, RMCPConfig

# Initialize outside handler for connection reuse
rmcp_app = None

def get_rmcp_app():
    """Get or create RMCP app."""
    global rmcp_app
    if rmcp_app is None:
        # Configure for Lambda environment
        config = RMCPConfig(
            default_timeout_ms=25000,  # Lambda timeout buffer
            retry_policy=RetryPolicy(
                max_attempts=2,  # Quick retries
                base_delay_ms=500
            )
        )
        
        # Create MCP session (implementation specific)
        mcp_session = create_lambda_mcp_session()
        rmcp_app = FastRMCP(mcp_session, config)
        
        # Initialize
        loop = asyncio.new_event_loop()
        loop.run_until_complete(rmcp_app.initialize())
    
    return rmcp_app

def lambda_handler(event, context):
    """AWS Lambda handler with RMCP."""
    tool_name = event.get('tool_name')
    arguments = event.get('arguments', {})
    idempotency_key = event.get('idempotency_key')
    
    if not tool_name:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'tool_name required'})
        }
    
    try:
        # Get RMCP app
        app = get_rmcp_app()
        
        # Execute tool call
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            app.call_tool(
                tool_name,
                arguments,
                idempotency_key=idempotency_key
            )
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result.result,
                'metadata': {
                    'request_id': result.rmcp_meta.request_id,
                    'attempts': result.rmcp_meta.attempts,
                    'duplicate': result.rmcp_meta.duplicate,
                    'remaining_time_ms': context.get_remaining_time_in_millis()
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

## Best Practices for Integration

### 1. Connection Management

```python
class ConnectionPool:
    """Manage RMCP connections efficiently."""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = []
        self.available = asyncio.Queue(maxsize=max_connections)
    
    async def acquire(self) -> FastRMCP:
        """Acquire a connection from pool."""
        if not self.connections:
            # Create initial connections
            for _ in range(self.max_connections):
                app = await self._create_connection()
                self.connections.append(app)
                await self.available.put(app)
        
        return await self.available.get()
    
    async def release(self, app: FastRMCP):
        """Return connection to pool."""
        await self.available.put(app)
    
    async def _create_connection(self) -> FastRMCP:
        """Create new RMCP connection."""
        mcp_session = await create_mcp_session()
        app = FastRMCP(mcp_session)
        await app.initialize()
        return app
```

### 2. Error Handling

```python
class IntegrationErrorHandler:
    """Unified error handling for integrations."""
    
    @staticmethod
    async def safe_call(app: FastRMCP, tool_name: str, arguments: dict):
        """Safe tool call with comprehensive error handling."""
        try:
            return await app.call_tool(tool_name, arguments)
        
        except ConnectionError:
            # Network issues - might retry
            logger.error("Connection error", exc_info=True)
            raise
        
        except TimeoutError:
            # Operation timeout - check if idempotent
            logger.warning(f"Timeout calling {tool_name}")
            raise
        
        except ValueError as e:
            # Validation error - don't retry
            logger.error(f"Invalid arguments for {tool_name}: {e}")
            raise
        
        except Exception as e:
            # Unknown error - log and re-raise
            logger.error(f"Unexpected error in {tool_name}", exc_info=True)
            raise
```

### 3. Testing Integration

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_rmcp_app():
    """Fixture for testing with RMCP."""
    app = AsyncMock(spec=FastRMCP)
    
    # Mock successful response
    app.call_tool.return_value = RMCPResult(
        result={"status": "success"},
        rmcp_meta=RMCPResponse(
            ack=True,
            processed=True,
            duplicate=False,
            attempts=1,
            request_id="test-123"
        )
    )
    
    return app

async def test_integration(mock_rmcp_app):
    """Test your integration."""
    result = await your_integration_function(mock_rmcp_app)
    
    assert result["success"] is True
    mock_rmcp_app.call_tool.assert_called_once()
```

## See Also

- [Advanced Examples](advanced.md) - Complex usage patterns  
- [Configuration Guide](../configuration.md) - Integration-specific config
- [Getting Started](../getting-started.md) - Basic setup

---

**Previous**: [Advanced Examples](advanced.md) | **Next**: [API Reference](../api/rmcp-session.md)