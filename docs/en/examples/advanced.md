# Advanced MCP-Tx Examples

This guide demonstrates advanced usage patterns and production-ready implementations using MCP-Tx.

## Multi-Step Workflows with Transaction Tracking

```python
from rmcp import FastMCP-Tx, RetryPolicy
import uuid

app = FastMCP-Tx(mcp_session)

class WorkflowManager:
    """Manage complex multi-step workflows with MCP-Tx reliability."""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.workflows = {}
    
    async def execute_data_pipeline(self, source_url: str) -> dict:
        """Execute a complete data processing pipeline."""
        workflow_id = str(uuid.uuid4())
        self.workflows[workflow_id] = {"status": "started", "steps": []}
        
        try:
            # Step 1: Download data with retry
            download_result = await self.app.call_tool(
                "download_data",
                {"url": source_url, "workflow_id": workflow_id},
                idempotency_key=f"download-{workflow_id}"
            )
            self._record_step(workflow_id, "download", download_result)
            
            # Step 2: Validate data
            validation_result = await self.app.call_tool(
                "validate_data",
                {
                    "file_path": download_result.result["path"],
                    "workflow_id": workflow_id
                },
                idempotency_key=f"validate-{workflow_id}"
            )
            self._record_step(workflow_id, "validate", validation_result)
            
            if not validation_result.result["valid"]:
                raise ValueError("Data validation failed")
            
            # Step 3: Process data with custom retry policy
            process_result = await self.app.call_tool(
                "process_data",
                {
                    "file_path": download_result.result["path"],
                    "workflow_id": workflow_id
                },
                retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=2000),
                idempotency_key=f"process-{workflow_id}"
            )
            self._record_step(workflow_id, "process", process_result)
            
            # Step 4: Upload results
            upload_result = await self.app.call_tool(
                "upload_results",
                {
                    "data": process_result.result,
                    "workflow_id": workflow_id
                },
                idempotency_key=f"upload-{workflow_id}"
            )
            self._record_step(workflow_id, "upload", upload_result)
            
            self.workflows[workflow_id]["status"] = "completed"
            return {
                "workflow_id": workflow_id,
                "result_url": upload_result.result["url"],
                "total_attempts": sum(
                    step["attempts"] for step in self.workflows[workflow_id]["steps"]
                )
            }
            
        except Exception as e:
            self.workflows[workflow_id]["status"] = "failed"
            self.workflows[workflow_id]["error"] = str(e)
            raise
    
    def _record_step(self, workflow_id: str, step_name: str, result):
        """Record workflow step execution."""
        self.workflows[workflow_id]["steps"].append({
            "name": step_name,
            "request_id": result.rmcp_meta.request_id,
            "attempts": result.rmcp_meta.attempts,
            "duplicate": result.rmcp_meta.duplicate
        })
```

## Circuit Breaker Pattern

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker pattern for MCP-Tx tools."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage with MCP-Tx
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

@app.tool()
async def protected_api_call(endpoint: str, data: dict) -> dict:
    """API call protected by circuit breaker."""
    return await breaker.call(external_api_call, endpoint, data)
```

## Distributed Tracing

```python
import contextvars
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Context variable for trace propagation
trace_context = contextvars.ContextVar('trace_context', default=None)

class TracedMCP-Tx:
    """MCP-Tx with distributed tracing support."""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.tracer = trace.get_tracer(__name__)
    
    async def call_tool_traced(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ) -> MCP-TxResult:
        """Call tool with distributed tracing."""
        with self.tracer.start_as_current_span(f"rmcp.{name}") as span:
            # Add trace context to arguments
            ctx = trace_context.get()
            if ctx:
                span.set_attribute("parent_trace_id", ctx)
            
            # Set span attributes
            span.set_attribute("tool.name", name)
            span.set_attribute("rmcp.idempotency_key", kwargs.get("idempotency_key", ""))
            
            try:
                # Execute tool call
                result = await self.app.call_tool(name, arguments, **kwargs)
                
                # Record result metadata
                span.set_attribute("rmcp.attempts", result.rmcp_meta.attempts)
                span.set_attribute("rmcp.duplicate", result.rmcp_meta.duplicate)
                span.set_attribute("rmcp.request_id", result.rmcp_meta.request_id)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

# Usage
traced_app = TracedMCP-Tx(app)
result = await traced_app.call_tool_traced("process_order", {"order_id": "12345"})
```

## Rate Limiting and Throttling

```python
import asyncio
from collections import deque
import time

class RateLimiter:
    """Token bucket rate limiter for MCP-Tx calls."""
    
    def __init__(self, rate: int, burst: int):
        self.rate = rate  # Tokens per second
        self.burst = burst  # Maximum burst size
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1):
        """Acquire tokens, waiting if necessary."""
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Calculate wait time
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)

class ThrottledMCP-Tx:
    """MCP-Tx with rate limiting."""
    
    def __init__(self, app: FastMCP-Tx, requests_per_second: int = 10):
        self.app = app
        self.limiter = RateLimiter(requests_per_second, requests_per_second * 2)
    
    async def call_tool_throttled(self, name: str, arguments: dict, **kwargs):
        """Call tool with rate limiting."""
        await self.limiter.acquire()
        return await self.app.call_tool(name, arguments, **kwargs)

# Usage
throttled_app = ThrottledMCP-Tx(app, requests_per_second=50)

# Burst of requests will be rate limited
tasks = [
    throttled_app.call_tool_throttled("api_call", {"id": i})
    for i in range(100)
]
results = await asyncio.gather(*tasks)
```

## Saga Pattern for Distributed Transactions

```python
from typing import List, Callable, Dict, Any
import logging

class SagaStep:
    """A step in a distributed saga."""
    
    def __init__(
        self,
        name: str,
        action: Callable,
        compensation: Callable,
        args: dict
    ):
        self.name = name
        self.action = action
        self.compensation = compensation
        self.args = args
        self.result = None

class DistributedSaga:
    """Implement saga pattern for distributed transactions."""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, steps: List[SagaStep]) -> Dict[str, Any]:
        """Execute saga with automatic compensation on failure."""
        completed_steps = []
        
        try:
            # Execute all steps
            for step in steps:
                self.logger.info(f"Executing saga step: {step.name}")
                
                result = await self.app.call_tool(
                    step.action,
                    step.args,
                    idempotency_key=f"saga-{step.name}-{id(steps)}"
                )
                
                step.result = result
                completed_steps.append(step)
                
            return {
                "success": True,
                "results": {step.name: step.result for step in steps}
            }
            
        except Exception as e:
            self.logger.error(f"Saga failed at step {len(completed_steps)}: {e}")
            
            # Compensate in reverse order
            for step in reversed(completed_steps):
                try:
                    self.logger.info(f"Compensating: {step.name}")
                    await self.app.call_tool(
                        step.compensation,
                        {
                            "original_args": step.args,
                            "original_result": step.result
                        },
                        idempotency_key=f"compensate-{step.name}-{id(steps)}"
                    )
                except Exception as comp_error:
                    self.logger.error(f"Compensation failed for {step.name}: {comp_error}")
            
            return {
                "success": False,
                "error": str(e),
                "compensated_steps": [s.name for s in completed_steps]
            }

# Example: Distributed order processing
saga = DistributedSaga(app)

order_saga = [
    SagaStep(
        name="reserve_inventory",
        action="inventory_service.reserve",
        compensation="inventory_service.release",
        args={"product_id": "ABC123", "quantity": 2}
    ),
    SagaStep(
        name="charge_payment",
        action="payment_service.charge",
        compensation="payment_service.refund",
        args={"amount": 99.99, "customer_id": "CUST456"}
    ),
    SagaStep(
        name="create_shipment",
        action="shipping_service.create",
        compensation="shipping_service.cancel",
        args={"address": "123 Main St", "items": ["ABC123"]}
    )
]

result = await saga.execute(order_saga)
```

## Event Sourcing Integration

```python
from datetime import datetime
import json

class EventStore:
    """Event store for MCP-Tx operations."""
    
    def __init__(self):
        self.events = []
    
    async def append(self, event: dict):
        """Append event to store."""
        self.events.append({
            **event,
            "timestamp": datetime.utcnow().isoformat(),
            "id": len(self.events)
        })

class EventSourcedMCP-Tx:
    """MCP-Tx with event sourcing."""
    
    def __init__(self, app: FastMCP-Tx, event_store: EventStore):
        self.app = app
        self.event_store = event_store
    
    async def call_tool_evented(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ) -> MCP-TxResult:
        """Call tool with event sourcing."""
        # Record command event
        await self.event_store.append({
            "type": "ToolCallRequested",
            "tool": name,
            "arguments": arguments,
            "metadata": kwargs
        })
        
        try:
            # Execute tool
            result = await self.app.call_tool(name, arguments, **kwargs)
            
            # Record success event
            await self.event_store.append({
                "type": "ToolCallCompleted",
                "tool": name,
                "request_id": result.rmcp_meta.request_id,
                "attempts": result.rmcp_meta.attempts,
                "duplicate": result.rmcp_meta.duplicate
            })
            
            return result
            
        except Exception as e:
            # Record failure event
            await self.event_store.append({
                "type": "ToolCallFailed",
                "tool": name,
                "error": str(e)
            })
            raise
    
    async def replay_events(self, filter_func=None):
        """Replay events for debugging or recovery."""
        for event in self.event_store.events:
            if filter_func and not filter_func(event):
                continue
            
            if event["type"] == "ToolCallRequested":
                # Could re-execute or just log
                print(f"Would replay: {event['tool']} with {event['arguments']}")
```

## Monitoring and Alerting

```python
from dataclasses import dataclass
from collections import defaultdict
import asyncio

@dataclass
class HealthMetrics:
    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    duplicate_count: int = 0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0

class MonitoredMCP-Tx:
    """MCP-Tx with comprehensive monitoring."""
    
    def __init__(self, app: FastMCP-Tx, alert_threshold: float = 0.95):
        self.app = app
        self.alert_threshold = alert_threshold
        self.metrics = defaultdict(HealthMetrics)
        self.alerts = []
    
    async def call_tool_monitored(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ) -> MCP-TxResult:
        """Call tool with monitoring."""
        metrics = self.metrics[name]
        
        try:
            result = await self.app.call_tool(name, arguments, **kwargs)
            
            # Update metrics
            metrics.success_count += 1
            metrics.total_attempts += result.rmcp_meta.attempts
            if result.rmcp_meta.duplicate:
                metrics.duplicate_count += 1
            
            return result
            
        except Exception as e:
            metrics.failure_count += 1
            
            # Check if we should alert
            if metrics.success_rate < self.alert_threshold:
                await self._send_alert(name, metrics)
            
            raise
    
    async def _send_alert(self, tool_name: str, metrics: HealthMetrics):
        """Send alert for degraded tool performance."""
        alert = {
            "tool": tool_name,
            "success_rate": metrics.success_rate,
            "total_calls": metrics.success_count + metrics.failure_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.alerts.append(alert)
        
        # In production, this would send to monitoring system
        logger.error(f"ALERT: Tool '{tool_name}' success rate: {metrics.success_rate:.2%}")
    
    def get_health_report(self) -> dict:
        """Get overall health report."""
        return {
            tool: {
                "success_rate": metrics.success_rate,
                "total_calls": metrics.success_count + metrics.failure_count,
                "avg_attempts": metrics.total_attempts / max(metrics.success_count, 1),
                "duplicate_rate": metrics.duplicate_count / max(metrics.success_count, 1)
            }
            for tool, metrics in self.metrics.items()
        }
```

## Integration Examples

### With FastAPI

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

api = FastAPI()
rmcp_app = FastMCP-Tx(mcp_session)

class ToolRequest(BaseModel):
    tool_name: str
    arguments: dict
    idempotency_key: str | None = None

@api.post("/execute-tool")
async def execute_tool(request: ToolRequest):
    """Execute MCP-Tx tool via REST API."""
    try:
        result = await rmcp_app.call_tool(
            request.tool_name,
            request.arguments,
            idempotency_key=request.idempotency_key
        )
        
        return {
            "success": True,
            "result": result.result,
            "metadata": {
                "request_id": result.rmcp_meta.request_id,
                "attempts": result.rmcp_meta.attempts,
                "duplicate": result.rmcp_meta.duplicate
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/health")
async def health_check():
    """Check MCP-Tx health."""
    tools = rmcp_app.list_tools()
    return {
        "status": "healthy",
        "registered_tools": len(tools),
        "tools": tools
    }
```

## See Also

- [Basic Examples](basic.md) - Simple usage patterns
- [Configuration Guide](../configuration.md) - Advanced configuration
- [Performance Guide](../performance.md) - Optimization strategies

---

**Previous**: [Basic Examples](basic.md) | **Next**: [Integration Guide](integration.md)