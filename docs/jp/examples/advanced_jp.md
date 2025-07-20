# 高度なMCP-Tx使用例

このガイドでは、MCP-Txを使用した高度な使用パターンと本番対応の実装を実演します。

## トランザクション追跡付きマルチステップワークフロー

```python
from mcp_tx import FastMCP-Tx, RetryPolicy
import uuid

app = FastMCP-Tx(mcp_session)

class WorkflowManager:
    """MCP-Tx信頼性を持つ複雑なマルチステップワークフローを管理"""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.workflows = {}
    
    async def execute_data_pipeline(self, source_url: str) -> dict:
        """完全なデータ処理パイプラインを実行"""
        workflow_id = str(uuid.uuid4())
        self.workflows[workflow_id] = {"status": "started", "steps": []}
        
        try:
            # ステップ1: リトライ付きデータダウンロード
            download_result = await self.app.call_tool(
                "download_data",
                {"url": source_url, "workflow_id": workflow_id},
                idempotency_key=f"download-{workflow_id}"
            )
            self._record_step(workflow_id, "download", download_result)
            
            # ステップ2: データ検証
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
                raise ValueError("データ検証に失敗")
            
            # ステップ3: カスタムリトライポリシーでデータ処理
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
            
            # ステップ4: 結果アップロード
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
        """ワークフローステップ実行を記録"""
        self.workflows[workflow_id]["steps"].append({
            "name": step_name,
            "request_id": result.rmcp_meta.request_id,
            "attempts": result.rmcp_meta.attempts,
            "duplicate": result.rmcp_meta.duplicate
        })
```

## サーキットブレーカーパターン

```python
import asyncio
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"  # 正常動作
    OPEN = "open"      # 失敗中、呼び出し拒否
    HALF_OPEN = "half_open"  # 回復テスト中

class CircuitBreaker:
    """MCP-Txツール用のサーキットブレーカーパターン"""
    
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
        """サーキットブレーカー保護付きで関数を実行"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("サーキットブレーカーがOPEN状態")
        
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

# MCP-Txでの使用例
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

@app.tool()
async def protected_api_call(endpoint: str, data: dict) -> dict:
    """サーキットブレーカーで保護されたAPI呼び出し"""
    return await breaker.call(external_api_call, endpoint, data)
```

## 分散トレーシング

```python
import contextvars
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# トレース伝播用のコンテキスト変数
trace_context = contextvars.ContextVar('trace_context', default=None)

class TracedMCP-Tx:
    """分散トレーシングサポート付きMCP-Tx"""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.tracer = trace.get_tracer(__name__)
    
    async def call_tool_traced(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ) -> MCP-TxResult:
        """分散トレーシング付きでツールを呼び出し"""
        with self.tracer.start_as_current_span(f"rmcp.{name}") as span:
            # トレースコンテキストを引数に追加
            ctx = trace_context.get()
            if ctx:
                span.set_attribute("parent_trace_id", ctx)
            
            # スパン属性設定
            span.set_attribute("tool.name", name)
            span.set_attribute("rmcp.idempotency_key", kwargs.get("idempotency_key", ""))
            
            try:
                # ツール呼び出し実行
                result = await self.app.call_tool(name, arguments, **kwargs)
                
                # 結果メタデータを記録
                span.set_attribute("rmcp.attempts", result.rmcp_meta.attempts)
                span.set_attribute("rmcp.duplicate", result.rmcp_meta.duplicate)
                span.set_attribute("rmcp.request_id", result.rmcp_meta.request_id)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

# 使用例
traced_app = TracedMCP-Tx(app)
result = await traced_app.call_tool_traced("process_order", {"order_id": "12345"})
```

## レート制限とスロットリング

```python
import asyncio
from collections import deque
import time

class RateLimiter:
    """MCP-Tx呼び出し用のトークンバケットレート制限器"""
    
    def __init__(self, rate: int, burst: int):
        self.rate = rate  # 秒あたりトークン数
        self.burst = burst  # 最大バーストサイズ
        self.tokens = burst
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1):
        """トークンを取得、必要に応じて待機"""
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # 待機時間を計算
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)

class ThrottledMCP-Tx:
    """レート制限付きMCP-Tx"""
    
    def __init__(self, app: FastMCP-Tx, requests_per_second: int = 10):
        self.app = app
        self.limiter = RateLimiter(requests_per_second, requests_per_second * 2)
    
    async def call_tool_throttled(self, name: str, arguments: dict, **kwargs):
        """レート制限付きでツールを呼び出し"""
        await self.limiter.acquire()
        return await self.app.call_tool(name, arguments, **kwargs)

# 使用例
throttled_app = ThrottledMCP-Tx(app, requests_per_second=50)

# リクエストのバーストはレート制限される
tasks = [
    throttled_app.call_tool_throttled("api_call", {"id": i})
    for i in range(100)
]
results = await asyncio.gather(*tasks)
```

## 分散トランザクション用Sagaパターン

```python
from typing import List, Callable, Dict, Any
import logging

class SagaStep:
    """分散Sagaのステップ"""
    
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
    """分散トランザクション用Sagaパターンの実装"""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, steps: List[SagaStep]) -> Dict[str, Any]:
        """失敗時の自動補償でSagaを実行"""
        completed_steps = []
        
        try:
            # すべてのステップを実行
            for step in steps:
                self.logger.info(f"Sagaステップ実行中: {step.name}")
                
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
            self.logger.error(f"Sagaがステップ{len(completed_steps)}で失敗: {e}")
            
            # 逆順で補償
            for step in reversed(completed_steps):
                try:
                    self.logger.info(f"補償中: {step.name}")
                    await self.app.call_tool(
                        step.compensation,
                        {
                            "original_args": step.args,
                            "original_result": step.result
                        },
                        idempotency_key=f"compensate-{step.name}-{id(steps)}"
                    )
                except Exception as comp_error:
                    self.logger.error(f"{step.name}の補償に失敗: {comp_error}")
            
            return {
                "success": False,
                "error": str(e),
                "compensated_steps": [s.name for s in completed_steps]
            }

# 例: 分散注文処理
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

## Django統合例

```python
# rmcp_django/middleware.py
from django.conf import settings
from mcp_tx import FastMCP-Tx, MCPTxConfig
import asyncio

class MCP-TxMiddleware:
    """MCP-Tx統合用Djangoミドルウェア"""
    
    _instance = None
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._setup_rmcp()
    
    def _setup_rmcp(self):
        """MCP-Tx接続を初期化"""
        if not MCP-TxMiddleware._instance:
            config = MCPTxConfig(
                default_timeout_ms=settings.MCP-Tx_TIMEOUT,
                enable_request_logging=settings.DEBUG
            )
            
            # 同期コンテキストで初期化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            mcp_session = self._create_mcp_session()
            MCP-TxMiddleware._instance = FastMCP-Tx(mcp_session, config)
            
            loop.run_until_complete(MCP-TxMiddleware._instance.initialize())
    
    def __call__(self, request):
        # リクエストにMCP-Txを付加
        request.rmcp = MCP-TxMiddleware._instance
        response = self.get_response(request)
        return response

# rmcp_django/views.py
from django.http import JsonResponse
from asgiref.sync import async_to_sync

def process_with_rmcp(request):
    """MCP-Txを使用するDjangoビュー"""
    tool_name = request.POST.get('tool')
    arguments = request.POST.get('arguments', {})
    
    # 同期コンテキストでMCP-Tx呼び出しを実行
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

## モニタリングとアラート

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
    """包括的なモニタリング付きMCP-Tx"""
    
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
        """モニタリング付きでツールを呼び出し"""
        metrics = self.metrics[name]
        
        try:
            result = await self.app.call_tool(name, arguments, **kwargs)
            
            # メトリクス更新
            metrics.success_count += 1
            metrics.total_attempts += result.rmcp_meta.attempts
            if result.rmcp_meta.duplicate:
                metrics.duplicate_count += 1
            
            return result
            
        except Exception as e:
            metrics.failure_count += 1
            
            # アラートを送信すべきかチェック
            if metrics.success_rate < self.alert_threshold:
                await self._send_alert(name, metrics)
            
            raise
    
    async def _send_alert(self, tool_name: str, metrics: HealthMetrics):
        """ツールパフォーマンス劣化のアラートを送信"""
        alert = {
            "tool": tool_name,
            "success_rate": metrics.success_rate,
            "total_calls": metrics.success_count + metrics.failure_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.alerts.append(alert)
        
        # 本番環境では、これはモニタリングシステムに送信される
        logger.error(f"アラート: ツール'{tool_name}'の成功率: {metrics.success_rate:.2%}")
    
    def get_health_report(self) -> dict:
        """全体的なヘルスレポートを取得"""
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

## FastAPI統合

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
    """REST API経由でMCP-Txツールを実行"""
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
    """MCP-Txヘルスをチェック"""
    tools = rmcp_app.list_tools()
    return {
        "status": "healthy",
        "registered_tools": len(tools),
        "tools": tools
    }
```

## 関連ドキュメント

- [基本例](basic_jp.md) - シンプルな使用パターン
- [設定ガイド](../configuration_jp.md) - 高度な設定
- [パフォーマンスガイド](../performance_jp.md) - 最適化戦略

---

**前へ**: [基本例](basic_jp.md) | **次へ**: [統合ガイド](integration_jp.md)