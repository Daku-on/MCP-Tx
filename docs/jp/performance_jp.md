# MCP-Txパフォーマンスガイド

このガイドでは、本番環境でのMCP-Txのパフォーマンス最適化戦略について説明します。

## パフォーマンス概要

MCP-Txは最小限のオーバーヘッドで信頼性機能を追加：
- **レイテンシオーバーヘッド**: リクエストあたり約1-5ms（ACK/NACK処理）
- **メモリオーバーヘッド**: アクティブリクエストあたり約1KB（重複排除追跡）
- **ネットワークオーバーヘッド**: リクエストあたり約200バイト（MCP-Txメタデータ）

## 即効性のあるパフォーマンス改善

### 1. タイムアウト最適化

```python
from mcp_tx import MCPTxConfig, FastMCP-Tx

# インタラクティブアプリケーション用の高速失敗設定
config = MCPTxConfig(
    default_timeout_ms=5000,  # 最大5秒待機
    retry_policy=RetryPolicy(
        max_attempts=2,  # クイックリトライのみ
        base_delay_ms=500
    )
)

app = FastMCP-Tx(mcp_session, config)
```

### 2. バッチ操作

```python
# シーケンシャル呼び出しの代わりに
results = []
for item in items:
    result = await app.call_tool("process", {"item": item})
    results.append(result)

# 並行実行を使用
import asyncio

async def process_item(item):
    return await app.call_tool("process", {"item": item})

# 並列処理（max_concurrent_requestsを尊重）
results = await asyncio.gather(*[
    process_item(item) for item in items
])
```

### 3. 接続プール

```python
# 複数の操作でセッションを再利用
async with FastMCP-Tx(mcp_session) as app:
    # すべての操作が同じ接続プールを共有
    for i in range(1000):
        await app.call_tool("operation", {"id": i})
```

## 同時実行最適化

### 同時実行制限の設定

```python
# 高同時実行設定
config = MCPTxConfig(
    max_concurrent_requests=50,  # 並列操作を増加
    default_timeout_ms=10000
)

# ツール毎の同時実行制御
@app.tool()
async def batch_processor(items: list) -> dict:
    """制御された同時実行でアイテムを処理"""
    semaphore = asyncio.Semaphore(10)  # 最大10並列
    
    async def process_one(item):
        async with semaphore:
            return await expensive_operation(item)
    
    results = await asyncio.gather(*[
        process_one(item) for item in items
    ])
    return {"processed": len(results)}
```

### 非同期ベストプラクティス

```python
# 良い例: 真の非同期操作
@app.tool()
async def efficient_io(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return {"data": await response.json()}

# 悪い例: 非同期でのブロッキング操作
@app.tool()
async def inefficient_io(url: str) -> dict:
    # これはイベントループをブロック！
    response = requests.get(url)  # ❌ 同期的
    return {"data": response.json()}
```

## メモリ最適化

### 重複排除ウィンドウのチューニング

```python
# 短期間操作: 小さなウィンドウ
config = MCPTxConfig(
    deduplication_window_ms=60000  # 1分
)

# 長時間実行ワークフロー: 大きなウィンドウ
config = MCPTxConfig(
    deduplication_window_ms=3600000  # 1時間
)

# メモリ使用量: ウィンドウ内の一意リクエストあたり約1KB
# 1時間ウィンドウ + 1000リクエスト/分 = 約60MBメモリ
```

### ツールレジストリ管理

```python
# ツールレジストリサイズを制限
app = FastMCP-Tx(
    mcp_session,
    max_tools=100  # 無制限の増加を防止
)

# 動的ツール登録/クリーンアップ
class ManagedApp:
    def __init__(self, mcp_session):
        self.app = FastMCP-Tx(mcp_session)
        self.tool_usage = {}
    
    def register_tool_with_ttl(self, tool_func, ttl_seconds=3600):
        """自動クリーンアップ付きでツールを登録"""
        self.app.tool()(tool_func)
        self.tool_usage[tool_func.__name__] = time.time()
        
        # クリーンアップをスケジュール
        asyncio.create_task(self._cleanup_tool(tool_func.__name__, ttl_seconds))
```

## ネットワーク最適化

### メッセージ圧縮

```python
# 大きなペイロード用の圧縮を有効化
config = MCPTxConfig(
    enable_compression=True,  # 1KB超のメッセージをGzip
    compression_threshold_bytes=1024
)

# 大きなデータ転送に効率的
@app.tool()
async def transfer_large_data(data: dict) -> dict:
    # 圧縮は自動的に実行
    return {"processed": len(json.dumps(data))}
```

### リトライ戦略最適化

```python
from mcp_tx import RetryPolicy

# ネットワーク最適化リトライ
network_retry = RetryPolicy(
    max_attempts=3,
    base_delay_ms=100,    # 高速開始
    max_delay_ms=5000,    # 5秒上限
    backoff_multiplier=3.0,  # 積極的バックオフ
    jitter=True  # サンダリングハード防止
)

# CPU集約的操作リトライ
cpu_retry = RetryPolicy(
    max_attempts=2,  # 高価な操作をリトライしない
    base_delay_ms=5000  # システム回復時間を与える
)
```

## モニタリングとプロファイリング

### パフォーマンスメトリクス

```python
import time
from contextlib import asynccontextmanager

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'total_calls': 0,
            'total_retries': 0,
            'total_time_ms': 0,
            'errors': 0
        }
    
    @asynccontextmanager
    async def track_call(self, tool_name: str):
        start = time.time()
        try:
            yield
            self.metrics['total_calls'] += 1
        except Exception as e:
            self.metrics['errors'] += 1
            raise
        finally:
            elapsed = (time.time() - start) * 1000
            self.metrics['total_time_ms'] += elapsed
            
            # 遅い操作をログ
            if elapsed > 1000:  # 1秒
                logger.warning(f"遅い操作: {tool_name}が{elapsed:.0f}ms要した")

# 使用例
monitor = PerformanceMonitor()

@app.tool()
async def monitored_operation(data: dict) -> dict:
    async with monitor.track_call("monitored_operation"):
        return await process_data(data)
```

### リソース使用量追跡

```python
import psutil
import asyncio

class ResourceMonitor:
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.baseline_memory = psutil.Process().memory_info().rss
    
    async def monitor_loop(self):
        """バックグラウンドモニタリングタスク"""
        while True:
            process = psutil.Process()
            current_memory = process.memory_info().rss
            memory_delta = (current_memory - self.baseline_memory) / 1024 / 1024  # MB
            
            logger.info(f"MCP-Tx統計: "
                       f"ツール: {len(self.app.list_tools())}, "
                       f"メモリ差分: {memory_delta:.1f}MB, "
                       f"CPU: {process.cpu_percent()}%")
            
            await asyncio.sleep(60)  # 毎分チェック
```

## 本番最適化

### ロードバランシング

```python
class LoadBalancedMCP-Tx:
    """複数のMCPセッション間で負荷分散"""
    
    def __init__(self, mcp_sessions: list):
        self.apps = [FastMCP-Tx(session) for session in mcp_sessions]
        self.current = 0
    
    async def call_tool(self, name: str, arguments: dict) -> MCP-TxResult:
        # ラウンドロビン選択
        app = self.apps[self.current]
        self.current = (self.current + 1) % len(self.apps)
        
        return await app.call_tool(name, arguments)
```

### キャッシュレイヤー

```python
from functools import lru_cache
import hashlib

class CachedMCP-Tx:
    """冪等操作にキャッシュを追加"""
    
    def __init__(self, app: FastMCP-Tx):
        self.app = app
        self.cache = {}
        self.cache_ttl = 300  # 5分
    
    async def call_tool_cached(self, name: str, arguments: dict) -> MCP-TxResult:
        # キャッシュキー生成
        cache_key = hashlib.md5(
            f"{name}:{json.dumps(arguments, sort_keys=True)}".encode()
        ).hexdigest()
        
        # キャッシュチェック
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result
        
        # 実行してキャッシュ
        result = await self.app.call_tool(name, arguments)
        self.cache[cache_key] = (result, time.time())
        
        return result
```

### 接続ウォームアップ

```python
async def warmup_rmcp(app: FastMCP-Tx):
    """より良いレイテンシのため接続を事前ウォームアップ"""
    # 接続プールを初期化
    await app.initialize()
    
    # 接続確立のためダミー操作を実行
    warmup_tasks = []
    for i in range(5):
        task = app.call_tool("ping", {}, timeout_ms=1000)
        warmup_tasks.append(task)
    
    # ウォームアップ完了を待機
    await asyncio.gather(*warmup_tasks, return_exceptions=True)
    
    logger.info("MCP-Tx接続プールがウォームアップ完了")
```

## パフォーマンスベンチマーク

### ベースライン性能

```python
async def benchmark_rmcp(app: FastMCP-Tx, iterations: int = 1000):
    """MCP-Txパフォーマンス特性を測定"""
    
    # シーケンシャル性能
    start = time.time()
    for i in range(iterations):
        await app.call_tool("echo", {"value": i})
    sequential_time = time.time() - start
    
    # 並行性能
    start = time.time()
    tasks = [
        app.call_tool("echo", {"value": i})
        for i in range(iterations)
    ]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start
    
    print(f"シーケンシャル: {iterations / sequential_time:.0f} ops/sec")
    print(f"並行: {iterations / concurrent_time:.0f} ops/sec")
    print(f"スピードアップ: {sequential_time / concurrent_time:.1f}x")
```

### 期待性能

| 操作タイプ | レイテンシ | スループット |
|---------------|---------|------------|
| 単純ツール呼び出し | 5-10ms | 100-200 ops/sec/接続 |
| リトライ付き（1回試行） | 10-20ms | 50-100 ops/sec/接続 |
| リトライ付き（3回試行） | 30-100ms | 10-30 ops/sec/接続 |
| 並行（10並列） | 5-10ms | 1000-2000 ops/sec総計 |

## 最適化チェックリスト

- [ ] **タイムアウト**: ユースケースに適切なタイムアウトを設定
- [ ] **同時実行**: max_concurrent_requestsを設定
- [ ] **リトライポリシー**: 信頼性vs性能のバランス
- [ ] **接続プール**: セッションを再利用
- [ ] **非同期操作**: すべてのI/Oが真に非同期であることを確認
- [ ] **バッチング**: 関連操作をグループ化
- [ ] **キャッシュ**: 冪等結果をキャッシュ
- [ ] **モニタリング**: パフォーマンスメトリクスを追跡
- [ ] **リソース制限**: メモリ制限を設定
- [ ] **圧縮**: 大きなペイロードで有効化

## 関連ドキュメント

- [設定ガイド](configuration_jp.md) - 詳細設定オプション
- [アーキテクチャ概要](architecture_jp.md) - MCP-Tx内部理解
- [トラブルシューティング](troubleshooting_jp.md) - 一般的な性能問題

---

**前へ**: [設定ガイド](configuration_jp.md) | **次へ**: [API リファレンス](api/rmcp-session_jp.md)