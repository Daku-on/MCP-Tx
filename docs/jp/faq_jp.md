# よくある質問

RMCP実装と使用に関する一般的な質問。

## 一般的な質問

### RMCPとは何ですか？

**RMCP (Reliable Model Context Protocol)** は、既存のMCPセッションをラップして配信保証、自動リトライ、リクエスト重複排除、拡張エラーハンドリングを提供する信頼性レイヤーです。標準MCPとの100%後方互換性があります。

### MCPサーバーを修正してRMCPを使用する必要がありますか？

**いいえ。** RMCPは後方互換性のために設計されています。既存のMCPサーバーで動作します：

- **RMCP対応サーバー**: 完全な信頼性機能（ACK/NACK、サーバーサイド重複排除）を取得
- **標準MCPサーバー**: クライアントサイド信頼性機能付き自動フォールバック

```python
# 任意のMCPサーバーで動作
rmcp_session = RMCPSession(your_mcp_session)
await rmcp_session.initialize()

print(f"RMCP有効: {rmcp_session.rmcp_enabled}")
# True = サーバーがRMCPサポート、False = フォールバックモード
```

### RMCPのパフォーマンス影響は？

**ほとんどのアプリケーションで最小限のオーバーヘッド**：

- **レイテンシ**: リクエストあたり< 1ms（メタデータ処理）
- **メモリ**: 約10-100KB（リクエスト追跡、重複排除キャッシュ）
- **ネットワーク**: リクエストあたり+200-500バイト（RMCPメタデータ）
- **CPU**: 無視できる程度（非同期操作、効率的キャッシング）

**ベンチマーク結果**（標準MCPとの比較）：
- 単純ツール呼び出し: +2-5%レイテンシ
- 高並行性: +1-3%レイテンシ  
- 大きなペイロード: < 1%レイテンシ影響

### 既存のMCPライブラリでRMCPを使用できますか？

**はい。** RMCPはMCPセッションインターフェースを実装する任意のオブジェクトをラップします：

```python
# 任意のMCPクライアントで動作
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport
from mcp.client.sse import SseClientTransport
from rmcp import RMCPSession

# 標準MCPクライアント
mcp_session = ClientSession(StdioClientTransport(...))
# または
mcp_session = ClientSession(SseClientTransport(...))

# RMCPでラップ
rmcp_session = RMCPSession(mcp_session)
```

## 設定に関する質問

### リトライ動作をカスタマイズするには？

セッションまたは呼び出しごとに`RetryPolicy`を使用してリトライ動作を設定：

```python
from rmcp import RMCPSession, RMCPConfig, RetryPolicy

# セッションレベルリトライポリシー
aggressive_retry = RetryPolicy(
    max_attempts=5,           # 最大5回試行
    base_delay_ms=2000,       # 2秒遅延から開始
    backoff_multiplier=2.0,   # 毎回遅延を倍増: 2s, 4s, 8s, 16s
    jitter=True,              # サンダリングハード防止のランダム性追加
    retryable_errors=[        # これらのエラータイプのみリトライ
        "CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED"
    ]
)

config = RMCPConfig(retry_policy=aggressive_retry)
rmcp_session = RMCPSession(mcp_session, config)

# または呼び出しごとのオーバーライド
quick_retry = RetryPolicy(max_attempts=2, base_delay_ms=500)
result = await rmcp_session.call_tool(
    "fast_operation", 
    {},
    retry_policy=quick_retry
)
```

### 最適な冪等性キー戦略は？

**操作とパラメータに基づいてユニークで決定的なキーを作成**：

```python
import hashlib
import json
from datetime import datetime

def create_idempotency_key(operation: str, params: dict, user_id: str = None) -> str:
    """操作用冪等性キーを作成"""
    
    # 操作タイプを含める
    key_parts = [operation]
    
    # 利用可能な場合ユーザーコンテキストを追加
    if user_id:
        key_parts.append(f"user-{user_id}")
    
    # パラメータから決定的ハッシュを作成
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    key_parts.append(params_hash)
    
    # 自然な期限切れのため日付を追加
    date_str = datetime.now().strftime("%Y%m%d")
    key_parts.append(date_str)
    
    return "-".join(key_parts)

# 使用例
idempotency_key = create_idempotency_key(
    "create_user",
    {"name": "Alice", "email": "alice@example.com"},
    user_id="admin_123"
)
# 結果: "create_user-admin_123-a1b2c3d4-20240115"

result = await rmcp_session.call_tool(
    "user_creator",
    {"name": "Alice", "email": "alice@example.com"},
    idempotency_key=idempotency_key
)
```

### 異なる操作のタイムアウトを設定するには？

**設定でデフォルトを設定し、操作ごとにオーバーライド**：

```python
# デフォルトタイムアウト設定
config = RMCPConfig(
    default_timeout_ms=10000,  # ほとんどの操作で10秒
)

rmcp_session = RMCPSession(mcp_session, config)

# 高速操作 - 短いタイムアウト
result = await rmcp_session.call_tool(
    "cache_lookup",
    {"key": "user_123"},
    timeout_ms=2000  # 2秒
)

# 低速操作 - 長いタイムアウト  
result = await rmcp_session.call_tool(
    "large_file_processor",
    {"file_path": "/data/huge_file.csv"},
    timeout_ms=300000  # 5分
)

# 重要操作 - 非常に長いタイムアウト
result = await rmcp_session.call_tool(
    "database_backup",
    {"target": "s3://backup-bucket"},
    timeout_ms=600000  # 10分（最大許可）
)
```

## エラーハンドリングに関する質問

### 異なるタイプのエラーを処理するには？

**対象を絞ったエラーハンドリングのため特定例外タイプを使用**：

```python
from rmcp.types import RMCPTimeoutError, RMCPNetworkError, RMCPError

async def robust_operation():
    try:
        result = await rmcp_session.call_tool("external_api", {"endpoint": "/data"})
        
        if result.ack:
            return result.result
        else:
            # ツールは実行されたがエラーを返した
            raise RuntimeError(f"ツール失敗: {result.rmcp_meta.error_message}")
            
    except RMCPTimeoutError as e:
        # タイムアウト処理 - より長いタイムアウトでリトライ
        print(f"操作が{e.details['timeout_ms']}ms後にタイムアウト")
        return await rmcp_session.call_tool(
            "external_api", 
            {"endpoint": "/data"},
            timeout_ms=60000  # より長いタイムアウト
        )
        
    except RMCPNetworkError as e:
        # ネットワーク問題処理 - 待ってからリトライ
        print(f"ネットワークエラー: {e.message}")
        await asyncio.sleep(5)
        return await rmcp_session.call_tool("external_api", {"endpoint": "/data"})
        
    except RMCPError as e:
        # その他のRMCPエラー処理
        if e.retryable:
            print(f"リトライ可能エラー: {e.message}")
            # RMCPが既にリトライしたので、ログして適切に処理
        else:
            print(f"永続エラー: {e.message}")
            # リトライしない、最終失敗として処理
        
        raise e
```

### `result.ack` vs `result.processed`の意味は？

**異なるレベルの保証**：

```python
result = await rmcp_session.call_tool("test_tool", {})

# result.ack = True の意味:
#   - リクエストがサーバーで受信された
#   - サーバーが処理を試行した
#   - サーバーが承認を返送した
#   - ネットワーク配信が成功した

# result.processed = True の意味:
#   - ツールが実際に実行された
#   - ツールが完了した（成功またはエラー）
#   - 結果がresult.resultで利用可能

# 可能な組み合わせ:
if result.ack and result.processed:
    # 最良ケース: 実行確認済み
    print(f"成功: {result.result}")
    
elif result.ack and not result.processed:
    # サーバーは受信したが処理できなかった
    print(f"サーバーエラー: {result.rmcp_meta.error_message}")
    
elif not result.ack:
    # ネットワーク/インフラ障害
    print(f"配信失敗: {result.rmcp_meta.error_message}")
    # このケースは自動リトライをトリガー
```

### RMCP問題をデバッグするには？

**RMCP内部を見るためデバッグログを有効化**：

```python
import logging

# RMCPデバッグログを有効化
logging.basicConfig(level=logging.DEBUG)
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# これでRMCPは以下をログ出力:
# - リクエストID生成
# - リトライ試行と遅延
# - キャッシュヒット/ミス
# - サーバー機能ネゴシエーション
# - エラー詳細

async with RMCPSession(mcp_session) as rmcp:
    await rmcp.initialize()
    
    # デバッグ情報をログで確認
    result = await rmcp.call_tool("test", {})
    
    # アクティブリクエストもチェック
    print(f"アクティブリクエスト: {len(rmcp.active_requests)}")
    for req_id, tracker in rmcp.active_requests.items():
        print(f"  {req_id}: {tracker.status} ({tracker.attempts} 試行)")
```

## 高度な使用方法に関する質問

### 複数のMCPサーバーでRMCPを使用できますか？

**はい、各サーバーに個別のRMCPセッションを作成**：

```python
# 異なる設定の複数サーバー
from rmcp import RMCPSession, RMCPConfig, RetryPolicy

# 高速、信頼性のあるサーバー - 最小限リトライ
fast_config = RMCPConfig(
    retry_policy=RetryPolicy(max_attempts=2, base_delay_ms=500),
    default_timeout_ms=5000
)
fast_rmcp = RMCPSession(fast_mcp_session, fast_config)

# 低速、信頼性の低いサーバー - 積極的リトライ
slow_config = RMCPConfig(
    retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=2000),
    default_timeout_ms=30000
)
slow_rmcp = RMCPSession(slow_mcp_session, slow_config)

# 各操作に適切なセッションを使用
fast_result = await fast_rmcp.call_tool("cache_lookup", {"key": "data"})
slow_result = await slow_rmcp.call_tool("ml_inference", {"model": "large"})
```

### サーキットブレーカーパターンを実装するには？

**手動サーキットブレーカー**（Session 2で自動版予定）：

```python
import time
from collections import defaultdict

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = defaultdict(int)
        self.last_failure = defaultdict(float)
    
    def is_open(self, tool_name: str) -> bool:
        """このツール用サーキットがオープンかチェック"""
        if self.failures[tool_name] >= self.failure_threshold:
            # タイムアウト経過をチェック
            if time.time() - self.last_failure[tool_name] > self.timeout:
                # サーキットブレーカーをリセット
                self.failures[tool_name] = 0
                return False
            return True
        return False
    
    def record_success(self, tool_name: str):
        """成功呼び出しを記録"""
        self.failures[tool_name] = 0
    
    def record_failure(self, tool_name: str):
        """失敗呼び出しを記録"""
        self.failures[tool_name] += 1
        self.last_failure[tool_name] = time.time()

# RMCPでの使用方法
circuit_breaker = CircuitBreaker()

async def call_with_circuit_breaker(tool_name: str, arguments: dict):
    if circuit_breaker.is_open(tool_name):
        raise RuntimeError(f"{tool_name}のサーキットブレーカーがオープン")
    
    try:
        result = await rmcp_session.call_tool(tool_name, arguments)
        
        if result.ack:
            circuit_breaker.record_success(tool_name)
            return result.result
        else:
            circuit_breaker.record_failure(tool_name)
            raise RuntimeError(f"ツール失敗: {result.rmcp_meta.error_message}")
            
    except Exception as e:
        circuit_breaker.record_failure(tool_name)
        raise e
```

## 統合に関する質問

### FastAPIでRMCPを統合するには？

**RMCPセッション用依存性注入を使用**：

```python
from fastapi import FastAPI, Depends, HTTPException
from rmcp import RMCPSession
import asyncio

app = FastAPI()

# グローバルRMCPセッション（または依存性注入を使用）
_rmcp_session = None

async def get_rmcp_session() -> RMCPSession:
    """RMCPセッション用FastAPI依存性"""
    global _rmcp_session
    if _rmcp_session is None:
        # RMCPセッションを初期化
        mcp_session = await setup_mcp_session()
        _rmcp_session = RMCPSession(mcp_session)
        await _rmcp_session.initialize()
    
    return _rmcp_session

@app.post("/process-file")
async def process_file(
    file_path: str,
    rmcp: RMCPSession = Depends(get_rmcp_session)
):
    """RMCPを使用してファイル処理"""
    try:
        result = await rmcp.call_tool(
            "file_processor",
            {"path": file_path},
            idempotency_key=f"process-{file_path.replace('/', '_')}"
        )
        
        if result.ack:
            return {
                "success": True,
                "result": result.result,
                "attempts": result.attempts
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"処理失敗: {result.rmcp_meta.error_message}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時にRMCPセッションをクリーンアップ"""
    global _rmcp_session
    if _rmcp_session:
        await _rmcp_session.close()
```

### asyncio.gather()でRMCPを使用するには？

**RMCPはasyncio並行性でシームレスに動作**：

```python
import asyncio

async def concurrent_operations():
    """複数のRMCP操作を並行実行"""
    
    # 並行操作のリストを作成
    operations = [
        rmcp_session.call_tool("processor_1", {"data": f"batch_{i}"})
        for i in range(10)
    ]
    
    # すべての操作を並行実行
    results = await asyncio.gather(*operations, return_exceptions=True)
    
    # 結果を処理
    successful_results = []
    failed_operations = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_operations.append((i, str(result)))
        elif result.ack:
            successful_results.append(result.result)
        else:
            failed_operations.append((i, result.rmcp_meta.error_message))
    
    print(f"成功: {len(successful_results)}")
    print(f"失敗: {len(failed_operations)}")
    
    return successful_results, failed_operations
```

## トラブルシューティング

### "ModuleNotFoundError: No module named 'rmcp'"

```bash
# RMCPをインストール
uv add rmcp
# または
pip install rmcp
```

### "RMCPResult object has no attribute 'content'"

```python
# ❌ 間違い: MCP結果に直接アクセス
result = await rmcp_session.call_tool("test", {})
print(result.content)  # AttributeError

# ✅ 正しい: result.resultでアクセス
result = await rmcp_session.call_tool("test", {})
if result.ack:
    print(result.result)  # これが実際のMCP結果
```

### "RMCP session not initialized"

```python
# ❌ 間違い: 初期化を忘れた
rmcp_session = RMCPSession(mcp_session)
result = await rmcp_session.call_tool("test", {})  # エラー

# ✅ 正しい: 常に最初に初期化
rmcp_session = RMCPSession(mcp_session)
await rmcp_session.initialize()  # 必須ステップ
result = await rmcp_session.call_tool("test", {})
```

### 高いメモリ使用量

```python
# メモリリークを防ぐためキャッシュ制限を設定
config = RMCPConfig(
    deduplication_window_ms=300000,  # デフォルト10分ではなく5分
    max_concurrent_requests=5,       # 並行リクエストを制限
)

rmcp_session = RMCPSession(mcp_session, config)
```

---

**前へ**: [移行ガイド](migration_jp.md) | **次へ**: [トラブルシューティング](troubleshooting_jp.md)