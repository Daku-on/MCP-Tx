# 基本的な使用例

一般的なMCP-Tx使用パターンの実践的な例。

## シンプルなツール呼び出し

### 基本的なファイル操作

```python
import asyncio
from mcp_tx import MCPTxSession

async def file_operations_example():
    """MCP-Tx信頼性付き基本ファイル操作"""
    
    # mcp_sessionは設定済みのMCPセッションと仮定
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # ファイル読み込み
        result = await rmcp.call_tool(
            "file_reader",
            {"path": "/path/to/data.txt"}
        )
        
        if result.ack:
            content = result.result.get("content", "")
            print(f"ファイル内容: {content}")
        else:
            print(f"ファイル読み込み失敗: {result.rmcp_meta.error_message}")
        
        # 冪等性付きファイル書き込み
        result = await rmcp.call_tool(
            "file_writer",
            {
                "path": "/path/to/output.txt",
                "content": "Hello, MCP-Tx!"
            },
            idempotency_key="write-hello-2024-01-15"
        )
        
        print(f"書き込み成功: {result.ack}")
        print(f"必要だった試行回数: {result.attempts}")

asyncio.run(file_operations_example())
```

### 信頼性付きAPI呼び出し

```python
import asyncio
import os
from mcp_tx import MCPTxSession, RetryPolicy

async def api_calls_example():
    """カスタムリトライポリシー付きAPI呼び出し"""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 重要操作用積極的リトライ付きAPI呼び出し
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
                "headers": {"Authorization": f"Bearer {os.environ['API_TOKEN']}"}
            },
            retry_policy=critical_retry,
            timeout_ms=30000
        )
        
        if result.ack:
            api_data = result.result
            print(f"APIレスポンス: {api_data}")
            print(f"{result.attempts}回の試行が必要でした")
        else:
            print(f"{result.attempts}回の試行後にAPI呼び出し失敗")
            print(f"エラー: {result.rmcp_meta.error_message}")

asyncio.run(api_calls_example())
```

## エラーハンドリングパターン

### 優雅なエラー復旧

```python
import asyncio
import logging
from mcp_tx import MCPTxSession
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError

async def error_handling_example():
    """堅牢なエラーハンドリングパターンのデモ"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 例1: フォールバック付きタイムアウト処理
        try:
            result = await rmcp.call_tool(
                "slow_operation",
                {"data_size": "large"},
                timeout_ms=5000  # 5秒タイムアウト
            )
            
            if result.ack:
                logger.info("操作が正常に完了")
                return result.result
                
        except MCP-TxTimeoutError as e:
            logger.warning(f"操作がタイムアウト: {e.message}")
            
            # フォールバック: より長いタイムアウトで試行
            try:
                result = await rmcp.call_tool(
                    "slow_operation",
                    {"data_size": "small"},  # より小さなデータセット
                    timeout_ms=15000  # より長いタイムアウト
                )
                logger.info("フォールバック操作が成功")
                return result.result
                
            except MCP-TxTimeoutError:
                logger.error("フォールバック操作もタイムアウト")
                return None
        
        # 例2: ネットワークエラー処理
        try:
            result = await rmcp.call_tool("external_api", {"endpoint": "/data"})
            
        except MCP-TxNetworkError as e:
            logger.warning(f"ネットワークエラー: {e.message}")
            
            # 待ってから一度リトライ
            await asyncio.sleep(2)
            
            try:
                result = await rmcp.call_tool("external_api", {"endpoint": "/data"})
                logger.info("ネットワークエラー後のリトライが成功")
                
            except MCP-TxNetworkError:
                logger.error("リトライ後もネットワークが利用不可")
                return None

asyncio.run(error_handling_example())
```

### 検証と入力サニタイゼーション

```python
import asyncio
from mcp_tx import MCPTxSession

async def validation_example():
    """入力検証とサニタイゼーションパターン"""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        def validate_file_path(path: str) -> str:
            """ファイルパスを検証・サニタイズ"""
            if not path or not path.strip():
                raise ValueError("ファイルパスは空にできません")
            
            # 潜在的なディレクトリトラバーサルを除去
            path = path.replace("..", "").replace("//", "/")
            
            # 絶対パスを確保
            if not path.startswith("/"):
                path = f"/safe_directory/{path}"
            
            return path
        
        def create_idempotency_key(operation: str, params: dict) -> str:
            """ユニークで説明的な冪等性キーを作成"""
            import hashlib
            import json
            from datetime import datetime
            
            # パラメータから決定的ハッシュを作成
            params_str = json.dumps(params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            
            # ユニーク性のためタイムスタンプを含める
            timestamp = datetime.now().strftime("%Y%m%d")
            
            return f"{operation}-{params_hash}-{timestamp}"
        
        # 例: 安全なファイル操作
        try:
            file_path = validate_file_path("../../../etc/passwd")  # 悪意のある入力
            
            result = await rmcp.call_tool(
                "file_reader",
                {"path": file_path},
                idempotency_key=create_idempotency_key("read", {"path": file_path})
            )
            
            if result.ack:
                print(f"安全にファイルを読み込み: {file_path}")
            
        except ValueError as e:
            print(f"無効な入力: {e}")
        
        # 例: パラメータ検証
        def validate_api_params(params: dict) -> dict:
            """APIパラメータを検証"""
            required_fields = ["endpoint", "method"]
            
            for field in required_fields:
                if field not in params:
                    raise ValueError(f"必須フィールドが不足: {field}")
            
            # メソッドをサニタイズ
            method = params["method"].upper()
            if method not in ["GET", "POST", "PUT", "DELETE"]:
                raise ValueError(f"無効なHTTPメソッド: {method}")
            params["method"] = method
            
            return params
        
        try:
            api_params = validate_api_params({
                "endpoint": "/users",
                "method": "get",  # GETに正規化される
                "data": {"name": "Alice"}
            })
            
            result = await rmcp.call_tool("http_client", api_params)
            
        except ValueError as e:
            print(f"無効なAPIパラメータ: {e}")

asyncio.run(validation_example())
```

## 並行性パターン

### 並列ツール実行

```python
import asyncio
from mcp_tx import MCPTxSession

async def parallel_execution_example():
    """MCP-Txで複数ツールを並行実行"""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 例1: 独立した並列操作
        async def process_file(file_path: str) -> dict:
            """単一ファイルを処理"""
            return await rmcp.call_tool(
                "file_processor",
                {"path": file_path, "operation": "analyze"},
                idempotency_key=f"analyze-{file_path.replace('/', '_')}"
            )
        
        # 複数ファイルを並列処理
        file_paths = ["/data/file1.txt", "/data/file2.txt", "/data/file3.txt"]
        
        tasks = [process_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"ファイル {file_paths[i]} 失敗: {result}")
            elif result.ack:
                successful_results.append(result.result)
                print(f"ファイル {file_paths[i]} 処理成功")
            else:
                print(f"ファイル {file_paths[i]} 処理失敗")
        
        print(f"{len(successful_results)}ファイルが正常に処理されました")
        
        # 例2: プロデューサー・コンシューマーパターン
        async def producer(queue: asyncio.Queue):
            """作業アイテムを生成"""
            for i in range(10):
                await queue.put(f"task_{i}")
            await queue.put(None)  # センチネル
        
        async def consumer(queue: asyncio.Queue, consumer_id: int):
            """作業アイテムを消費・処理"""
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
                        print(f"コンシューマー {consumer_id} が {item} を処理")
                    
                except Exception as e:
                    print(f"コンシューマー {consumer_id} が {item} で失敗: {e}")
                
                finally:
                    queue.task_done()
            
            return processed
        
        # プロデューサー・コンシューマーパターンを実行
        work_queue = asyncio.Queue(maxsize=20)
        
        # プロデューサーとコンシューマーを開始
        producer_task = asyncio.create_task(producer(work_queue))
        consumer_tasks = [
            asyncio.create_task(consumer(work_queue, i)) 
            for i in range(3)
        ]
        
        # 完了を待機
        await producer_task
        await work_queue.join()
        
        # コンシューマー結果を取得
        consumer_results = await asyncio.gather(*consumer_tasks)
        total_processed = sum(consumer_results)
        print(f"合計処理アイテム数: {total_processed}")

asyncio.run(parallel_execution_example())
```

### レート制限操作

```python
import asyncio
from mcp_tx import MCPTxSession

class RateLimiter:
    """API呼び出し用シンプルレート制限器"""
    
    def __init__(self, calls_per_second: float):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
    
    async def acquire(self):
        """レート制限を守るため必要に応じて待機"""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_call
        
        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)
        
        self.last_call = asyncio.get_event_loop().time()

async def rate_limited_example():
    """MCP-Txでレート制限API呼び出し"""
    
    # 毎秒2回の呼び出しに制限
    rate_limiter = RateLimiter(calls_per_second=2.0)
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        async def rate_limited_api_call(endpoint: str) -> dict:
            """レート制限API呼び出しを実行"""
            await rate_limiter.acquire()
            
            return await rmcp.call_tool(
                "api_client",
                {"endpoint": endpoint},
                idempotency_key=f"api-{endpoint.replace('/', '_')}"
            )
        
        # レート制限を守って複数API呼び出し
        endpoints = [f"/users/{i}" for i in range(1, 11)]
        
        start_time = asyncio.get_event_loop().time()
        
        tasks = [rate_limited_api_call(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        
        successful_calls = sum(1 for result in results if result.ack)
        print(f"{end_time - start_time:.2f}秒で{successful_calls}回のAPI呼び出しを完了")

asyncio.run(rate_limited_example())
```

## 設定例

### 環境固有設定

```python
import os
from mcp_tx import MCPTxSession, MCPTxConfig, RetryPolicy

def create_rmcp_config() -> MCPTxConfig:
    """環境固有のMCP-Tx設定を作成"""
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        return MCPTxConfig(
            default_timeout_ms=30000,  # 30秒
            retry_policy=RetryPolicy(
                max_attempts=5,
                base_delay_ms=2000,     # 2秒
                backoff_multiplier=2.0,
                jitter=True
            ),
            max_concurrent_requests=20,
            deduplication_window_ms=600000,  # 10分
            enable_transactions=True,
            enable_monitoring=True
        )
    
    elif environment == "staging":
        return MCPTxConfig(
            default_timeout_ms=15000,  # 15秒
            retry_policy=RetryPolicy(
                max_attempts=3,
                base_delay_ms=1000,     # 1秒
                backoff_multiplier=1.5,
                jitter=True
            ),
            max_concurrent_requests=10,
            deduplication_window_ms=300000,  # 5分
        )
    
    else:  # development
        return MCPTxConfig(
            default_timeout_ms=5000,   # 5秒
            retry_policy=RetryPolicy(
                max_attempts=2,
                base_delay_ms=500,      # 0.5秒
                backoff_multiplier=1.0, # 高速開発サイクルのためバックオフなし
                jitter=False
            ),
            max_concurrent_requests=5,
            deduplication_window_ms=60000,   # 1分
        )

async def environment_config_example():
    """環境固有設定を使用"""
    
    config = create_rmcp_config()
    
    async with MCPTxSession(mcp_session, config) as rmcp:
        await rmcp.initialize()
        
        print(f"環境: {os.getenv('ENVIRONMENT', 'development')}")
        print(f"最大並行数: {config.max_concurrent_requests}")
        print(f"デフォルトタイムアウト: {config.default_timeout_ms}ms")
        print(f"最大リトライ試行回数: {config.retry_policy.max_attempts}")
        
        # 設定済みセッションを使用
        result = await rmcp.call_tool("test_tool", {})
        print(f"テスト成功: {result.ack}")
```

## バッチ処理パターン

### 大量データ処理

```python
import asyncio
from mcp_tx import MCPTxSession
from typing import List, Tuple, Any

async def batch_processing_example():
    """大量データの効率的バッチ処理"""
    
    async with MCPTxSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        async def process_batch(items: List[dict], batch_id: int) -> Tuple[List[Any], List[Tuple[dict, str]]]:
            """アイテムのバッチを処理"""
            results = []
            failures = []
            
            for item in items:
                try:
                    result = await rmcp.call_tool(
                        "item_processor",
                        {"item": item},
                        idempotency_key=f"batch-{batch_id}-item-{item['id']}",
                        timeout_ms=10000
                    )
                    
                    if result.ack:
                        results.append(result.result)
                    else:
                        failures.append((item, result.rmcp_meta.error_message))
                        
                except Exception as e:
                    failures.append((item, str(e)))
            
            return results, failures
        
        # 大きなデータセットをバッチに分割
        all_items = [{"id": i, "data": f"item_{i}"} for i in range(100)]
        batch_size = 10
        batches = [
            all_items[i:i + batch_size] 
            for i in range(0, len(all_items), batch_size)
        ]
        
        # バッチを並列処理
        batch_tasks = [
            process_batch(batch, batch_id) 
            for batch_id, batch in enumerate(batches)
        ]
        
        batch_results = await asyncio.gather(*batch_tasks)
        
        # 結果を集約
        all_results = []
        all_failures = []
        
        for results, failures in batch_results:
            all_results.extend(results)
            all_failures.extend(failures)
        
        print(f"成功: {len(all_results)}, 失敗: {len(all_failures)}")
        print(f"成功率: {len(all_results) / len(all_items) * 100:.1f}%")

asyncio.run(batch_processing_example())
```

## 統合パターン

### Webアプリケーション統合

```python
from mcp_tx import MCPTxSession
import asyncio

class WebAppMCP-TxClient:
    """Webアプリケーション用MCP-Txクライアント"""
    
    def __init__(self, mcp_session):
        self.rmcp_session = MCPTxSession(mcp_session)
        self.initialized = False
    
    async def initialize(self):
        """クライアントを初期化"""
        if not self.initialized:
            await self.rmcp_session.initialize()
            self.initialized = True
    
    async def handle_user_request(self, user_id: str, operation: str, data: dict) -> dict:
        """ユーザーリクエストを処理"""
        await self.initialize()
        
        # ユーザー固有の冪等性キーを作成
        idempotency_key = f"user-{user_id}-{operation}-{hash(str(data))}"
        
        try:
            result = await self.rmcp_session.call_tool(
                f"user_{operation}",
                {"user_id": user_id, **data},
                idempotency_key=idempotency_key,
                timeout_ms=30000
            )
            
            return {
                "success": result.ack,
                "data": result.result if result.ack else None,
                "error": result.rmcp_meta.error_message if not result.ack else None,
                "attempts": result.attempts
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "attempts": 1
            }
    
    async def close(self):
        """クライアントをクローズ"""
        if self.rmcp_session:
            await self.rmcp_session.close()

# 使用例
async def web_app_example():
    web_client = WebAppMCP-TxClient(mcp_session)
    
    try:
        # ユーザーリクエストを処理
        response = await web_client.handle_user_request(
            user_id="user123",
            operation="create_order", 
            data={"product": "laptop", "quantity": 1}
        )
        
        print(f"リクエスト処理結果: {response}")
        
    finally:
        await web_client.close()

asyncio.run(web_app_example())
```

---

**次へ**: [高度な例](advanced_jp.md) →