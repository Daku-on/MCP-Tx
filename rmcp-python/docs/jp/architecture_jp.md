# RMCPアーキテクチャ概要

RMCPがどのようにMCPに信頼性保証を追加するかを理解する。

## ハイレベルアーキテクチャ

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│                 │    │                      │    │                 │
│  クライアント   │    │    RMCPセッション    │    │   MCPサーバー   │
│  アプリケーション│    │   (信頼性ラッパー)    │    │   (既存)        │
│                 │    │                      │    │                 │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
         │                        │                          │
         │ call_tool()            │ 拡張MCP                  │ 標準MCP  
         ├─────────────────────▶  │ _meta.rmcp付き          ├──────────────▶
         │                        │                          │
         │ RMCPResult             │ 標準MCP                  │ ツール結果
         ◀─────────────────────── │ レスポンス               ◀──────────────┤
         │                        │                          │
```

## コアコンポーネント

### 1. RMCPSession（ラッパー）

既存のMCPセッションをラップするメインインターフェース：

```python
class RMCPSession:
    def __init__(self, mcp_session: BaseSession, config: RMCPConfig = None):
        self.mcp_session = mcp_session  # 既存のMCPセッション
        self.config = config or RMCPConfig()
        # ... 信頼性インフラストラクチャ
```

**主な責務**：
- ✅ サーバーとの機能ネゴシエーション
- ✅ リクエストID生成と追跡
- ✅ ACK/NACK処理  
- ✅ 指数バックオフによるリトライロジック
- ✅ 冪等性ベースの重複排除
- ✅ トランザクションライフサイクル管理
- ✅ 標準MCPへの透明なフォールバック

### 2. メッセージ拡張

RMCPは標準MCPメッセージを信頼性メタデータで拡張：

```json
{
  "method": "tools/call",
  "params": {
    "name": "file_reader",
    "arguments": {"path": "/data.txt"},
    "_meta": {
      "rmcp": {
        "version": "0.1.0",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
        "transaction_id": "txn_123456789",
        "idempotency_key": "read_data_v1",
        "expect_ack": true,
        "retry_count": 0,
        "timeout_ms": 30000,
        "timestamp": "2024-01-15T10:30:00Z"
      }
    }
  }
}
```

### 3. リクエストライフサイクル

```
リクエスト作成
      │
      ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   PENDING   │───▶│     SENT     │───▶│ ACKNOWLEDGED│
└─────────────┘    └──────────────┘    └─────────────┘
      │                     │                   │
      │            ┌────────▼────────┐          │
      │            │     FAILED      │          │
      ▼            └─────────────────┘          ▼
┌─────────────┐              │             ┌─────────────┐
│   TIMEOUT   │              │             │  COMPLETED  │
└─────────────┘              │             └─────────────┘
      │                      │                   │
      └──────────────────────┼───────────────────┘
                             ▼
                    ┌─────────────────┐
                    │   リトライロジック  │
                    │ (リトライ可能な場合) │
                    └─────────────────┘
```

## 信頼性機能詳細

### 1. ACK/NACKメカニズム

**承認フロー**：
```python
# クライアントがexpect_ack=trueでリクエスト送信
request = {
    "_meta": {"rmcp": {"expect_ack": True, ...}},
    ...
}

# サーバーが処理してACKで応答
response = {
    "result": {...},
    "_meta": {
        "rmcp": {
            "ack": True,           # 明示的な承認
            "processed": True,     # ツールが実行された
            "request_id": "...",   # 関連付け
        }
    }
}

# クライアントがACKを検証してRMCPResultを返す
```

### 2. 指数バックオフによるリトライロジック

```python
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 1000
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_errors: list[str] = [
        "CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR", "TEMPORARY_FAILURE"
    ]

def calculate_delay(attempt: int, policy: RetryPolicy) -> int:
    # ベース遅延 * 乗数^試行回数
    delay = policy.base_delay_ms * (policy.backoff_multiplier ** attempt)
    delay = min(delay, policy.max_delay_ms)
    
    if policy.jitter:
        # サンダリングハード防止のため±20%ジッターを追加
        jitter = delay * 0.2 * (random.random() * 2 - 1)
        delay = int(delay + jitter)
    
    return max(delay, policy.base_delay_ms)
```

### 3. 冪等性と重複排除

**キャッシュベース重複排除**：
```python
class RMCPSession:
    def __init__(self):
        # メモリ安全性のためのTTL付きLRUキャッシュ
        self._deduplication_cache: dict[str, tuple[RMCPResult, datetime]] = {}
    
    def _get_cached_result(self, idempotency_key: str) -> RMCPResult | None:
        if idempotency_key in self._deduplication_cache:
            cached_result, timestamp = self._deduplication_cache[idempotency_key]
            
            # TTLチェック（デフォルト: 5分）
            if timestamp + timedelta(milliseconds=self.config.deduplication_window_ms) > datetime.utcnow():
                # duplicate=Trueでコピーを返す
                return self._create_duplicate_response(cached_result)
            else:
                # 期限切れ、キャッシュから削除
                del self._deduplication_cache[idempotency_key]
        
        return None
```

### 4. 並行リクエスト管理

```python
class RMCPSession:
    def __init__(self, config: RMCPConfig):
        # 並行性制御用セマフォ
        self._request_semaphore = anyio.Semaphore(config.max_concurrent_requests)
        
        # アクティブリクエスト追跡
        self._active_requests: dict[str, RequestTracker] = {}
    
    async def call_tool(self, ...):
        # 処理前にセマフォを取得
        async with self._request_semaphore:
            return await self._call_tool_with_retry(...)
```

## 機能ネゴシエーション

RMCPはMCPの実験的機能を使用して機能をネゴシエート：

### クライアント広告

```python
# 初期化中、RMCPは機能を広告
kwargs["capabilities"]["experimental"]["rmcp"] = {
    "version": "0.1.0",
    "features": ["ack", "retry", "idempotency", "transactions"]
}
```

### サーバー応答

```python
# サーバーがサポートするRMCP機能で応答
server_capabilities = {
    "experimental": {
        "rmcp": {
            "version": "0.1.0", 
            "features": ["ack", "retry"]  # クライアント機能のサブセット
        }
    }
}
```

### フォールバック動作

```python
if not self._rmcp_enabled:
    # 標準MCPへの透明なフォールバック
    return await self._execute_standard_mcp_call(name, arguments, timeout_ms)
else:
    # RMCPメタデータ付き拡張MCP
    return await self._execute_rmcp_call(name, arguments, rmcp_meta, timeout_ms)
```

## パフォーマンス特性

### メモリ使用量
- **リクエスト追跡**: O(並行リクエスト数) - 通常10-100リクエスト
- **重複排除キャッシュ**: O(ユニーク冪等性キー数) TTLベース削除付き
- **設定**: 最小オーバーヘッド（セッションあたり約1KB）

### レイテンシ影響
- **RMCPオーバーヘッド**: リクエストあたり< 1ms（メタデータ処理）
- **ネットワークオーバーヘッド**: リクエストあたり+200-500バイト（RMCPメタデータ）
- **リトライ遅延**: 設定可能な指数バックオフ（デフォルト: 1s, 2s, 4s）

### スループット
- **並行リクエスト**: 設定可能制限（デフォルト: 10）
- **レート制限**: オプション（MVP未実装）
- **非同期パフォーマンス**: 高並行性のためのネイティブanyioサポート

## エラーハンドリング戦略

### エラー分類
```python
class RMCPError(Exception):
    def __init__(self, message: str, error_code: str, retryable: bool):
        self.retryable = retryable  # リトライ動作を決定

# 特定エラータイプ
RMCPTimeoutError(retryable=True)    # タイムアウト時リトライ
RMCPNetworkError(retryable=True)    # ネットワーク問題時リトライ  
RMCPSequenceError(retryable=False)  # シーケンスエラー時リトライしない
```

### エラー伝播
1. **一時エラー**: バックオフ付き自動リトライ
2. **永続エラー**: 即座に失敗、リトライなし
3. **不明エラー**: 設定可能なリトライ動作

## セキュリティ考慮事項

### リクエストID生成
```python
# 暗号学的に安全なUUID生成
request_id = str(uuid.uuid4())  # ID予測/衝突を防ぐ
```

### エラーメッセージサニタイゼーション
```python
def _sanitize_error_message(self, error: Exception) -> str:
    # エラーメッセージから機密情報を除去
    patterns = [
        r"password[=:]\\s*\\S+", r"token[=:]\\s*\\S+", 
        r"key[=:]\\s*\\S+", r"/Users/[^/\\s]+", r"/home/[^/\\s]+"
    ]
    # ... サニタイゼーションロジック
```

### 機能検証
- ネゴシエーション中にサーバー機能を検証
- 不明/unsafe機能は無視
- サポートされない機能に対するグレースフル劣化

## 次のステップ

- [**設定ガイド**](configuration_jp.md) - RMCP動作をカスタマイズ
- [**APIリファレンス**](api/rmcp-session_jp.md) - 詳細なメソッドドキュメント
- [**パフォーマンスガイド**](performance_jp.md) - 最適化とチューニング

---

**前へ**: [はじめる](getting-started_jp.md) | **次へ**: [信頼性機能](reliability-features_jp.md)