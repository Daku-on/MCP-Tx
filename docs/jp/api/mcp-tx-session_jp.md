# MCPTxSession APIリファレンス

信頼性のあるMCPツール呼び出しのメインインターフェース。

## クラス: MCPTxSession

```python
class MCPTxSession:
    """
    信頼性機能付きで既存のMCPセッションをラップするMCP-Txセッション。
    
    提供機能:
    - ACK/NACK保証
    - 指数バックオフ付き自動リトライ  
    - 冪等性キーによるリクエスト重複排除
    - トランザクション追跡
    - MCPとの100%後方互換性
    """
```

### コンストラクタ

```python
def __init__(self, mcp_session: BaseSession, config: MCPTxConfig | None = None)
```

**パラメータ**:
- `mcp_session` (`BaseSession`): ラップする既存のMCPセッション
- `config` (`MCPTxConfig`, オプション): MCP-Tx設定。デフォルトは`MCPTxConfig()`

**例**:
```python
from mcp_tx import MCPTxSession, MCPTxConfig
from mcp.client.session import ClientSession

mcp_session = ClientSession(...)
config = MCPTxConfig(default_timeout_ms=10000)
rmcp_session = MCPTxSession(mcp_session, config)
```

### メソッド

#### initialize()

```python
async def initialize(self, **kwargs) -> Any
```

MCP-Tx機能ネゴシエーション付きでセッションを初期化。

**パラメータ**:
- `**kwargs`: 基盤となるMCPセッションの`initialize()`に渡される

**戻り値**: 基盤となるMCPセッション初期化からの結果

**動作**:
- 初期化にMCP-Tx実験的機能を追加
- サーバーのMCP-Txサポートを検出
- サーバー機能に基づいてMCP-Tx機能を有効/無効化

**例**:
```python
result = await rmcp_session.initialize(
    capabilities={"tools": {"list_changed": True}}
)
print(f"MCP-Tx有効: {rmcp_session.rmcp_enabled}")
```

#### call_tool()

```python
async def call_tool(
    self,
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    idempotency_key: str | None = None,
    timeout_ms: int | None = None,
    retry_policy: RetryPolicy | None = None,
) -> MCP-TxResult
```

MCP-Tx信頼性保証付きでツールを呼び出し。

**パラメータ**:
- `name` (`str`): ツール名（英数字、ハイフン、アンダースコアのみ）
- `arguments` (`dict[str, Any]`, オプション): ツール引数。デフォルトは`{}`
- `idempotency_key` (`str`, オプション): 重複排除用のユニークキー
- `timeout_ms` (`int`, オプション): デフォルトタイムアウトをオーバーライド（1-600,000ms）
- `retry_policy` (`RetryPolicy`, オプション): デフォルトリトライポリシーをオーバーライド

**戻り値**: ツール結果とMCP-Txメタデータを含む`MCP-TxResult`

**例外**:
- `ValueError`: 無効な入力パラメータ
- `MCP-TxTimeoutError`: 操作がタイムアウト
- `MCP-TxNetworkError`: ネットワーク/接続エラー
- `MCP-TxError`: その他のMCP-Tx固有エラー

**例**:
```python
# 基本ツール呼び出し
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

# 冪等性付き
result = await rmcp_session.call_tool(
    "file_writer",
    {"path": "/output.txt", "content": "Hello"},
    idempotency_key="write-hello-v1"
)

# カスタムリトライとタイムアウト付き
custom_retry = RetryPolicy(max_attempts=5, base_delay_ms=500)
result = await rmcp_session.call_tool(
    "api_call",
    {"url": "https://api.example.com"},
    retry_policy=custom_retry,
    timeout_ms=15000
)
```

#### close()

```python
async def close(self) -> None
```

MCP-Txセッションと基盤となるMCPセッションをクローズ。

**動作**:
- アクティブリクエストの完了を短時間待機
- `close()`メソッドがある場合、基盤となるMCPセッションをクローズ
- 内部キャッシュとリクエスト追跡をクリア

**例**:
```python
await rmcp_session.close()

# または非同期コンテキストマネージャーとして使用
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    result = await rmcp.call_tool("echo", {"msg": "Hello"})
    # 終了時に自動的にクローズ
```

### プロパティ

#### rmcp_enabled

```python
@property
def rmcp_enabled(self) -> bool
```

このセッションでMCP-Tx機能が有効かどうか。

**戻り値**: サーバーがMCP-Txをサポートする場合`True`、標準MCPにフォールバックする場合`False`

**例**:
```python
await rmcp_session.initialize()
if rmcp_session.rmcp_enabled:
    print("✅ MCP-Tx機能アクティブ")
else:
    print("⚠️ 標準MCPにフォールバック")
```

#### active_requests

```python
@property  
def active_requests(self) -> dict[str, RequestTracker]
```

現在アクティブなMCP-Txリクエスト。

**戻り値**: リクエストIDを`RequestTracker`オブジェクトにマップする辞書

**例**:
```python
print(f"アクティブリクエスト: {len(rmcp_session.active_requests)}")
for request_id, tracker in rmcp_session.active_requests.items():
    print(f"  {request_id}: {tracker.status} ({tracker.attempts} 試行)")
```

### 非同期コンテキストマネージャー

`MCPTxSession`は非同期コンテキストマネージャープロトコルをサポート：

```python
async def __aenter__(self) -> MCPTxSession: ...
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

**例**:
```python
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    
    result = await rmcp.call_tool("test", {})
    print(f"結果: {result.result}")
    
    # 終了時にセッション自動クローズ
```

## MCP-TxResult

`call_tool()`が返す結果オブジェクト。

```python
@dataclass
class MCP-TxResult:
    """MCP結果とMCP-Txメタデータの両方を含む結果ラッパー"""
    
    result: Any                    # MCPからの実際のツール結果
    rmcp_meta: MCP-TxResponse       # MCP-Txメタデータとステータス
```

### プロパティ

```python
@property
def ack(self) -> bool:
    """リクエストが承認されたかどうか"""
    return self.rmcp_meta.ack

@property  
def processed(self) -> bool:
    """ツールが実際に実行されたかどうか"""
    return self.rmcp_meta.processed

@property
def final_status(self) -> str:
    """最終ステータス: 'completed' または 'failed'"""
    return self.rmcp_meta.final_status

@property
def attempts(self) -> int:
    """実行されたリトライ試行回数"""
    return self.rmcp_meta.attempts
```

### 使用例

```python
result = await rmcp_session.call_tool("calculator", {"op": "add", "a": 1, "b": 2})

# MCP-Tx保証をチェック
assert result.ack == True           # リクエストが承認された
assert result.processed == True     # ツールが実行された  
assert result.final_status == "completed"
assert result.attempts >= 1         # 少なくとも1回の試行

# 実際の結果にアクセス
if result.ack:
    calculation_result = result.result
    print(f"合計: {calculation_result}")
else:
    print(f"失敗: {result.rmcp_meta.error_message}")
```

## エラーハンドリング

### 例外階層

```python
MCP-TxError (ベース)
├── MCP-TxTimeoutError      # タイムアウト発生
├── MCP-TxNetworkError      # ネットワーク/接続問題  
└── MCP-TxSequenceError     # シーケンス/順序エラー
```

### エラー属性

すべてのMCP-Txエラーには以下があります:
- `message`: 人間が読めるエラー説明
- `error_code`: 機械が読めるエラーコード
- `retryable`: エラーがリトライをトリガーすべきかどうか
- `details`: 追加のエラーコンテキスト

### エラーハンドリング例

```python
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError

try:
    result = await rmcp_session.call_tool("slow_api", {})
except MCP-TxTimeoutError as e:
    print(f"{e.details['timeout_ms']}ms後にタイムアウト")
    # より長いタイムアウトでリトライ
except MCP-TxNetworkError as e:
    print(f"ネットワークエラー: {e.message}")
    # 接続をチェック
except ValueError as e:
    print(f"無効な入力: {e}")
    # 入力パラメータを修正
```

## ベストプラクティス

### 1. リソース管理

```python
# ✅ 良い: 非同期コンテキストマネージャーを使用
async with MCPTxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    # ... rmcpを使用
    # 自動的にクリーンアップ

# ⚠️ 許容: 手動クリーンアップ  
rmcp = MCPTxSession(mcp_session)
try:
    await rmcp.initialize()
    # ... rmcpを使用
finally:
    await rmcp.close()
```

### 2. 冪等性キー

```python
# ✅ 良い: 説明的でユニークなキーを使用
await rmcp.call_tool(
    "create_user",
    {"name": "Alice", "email": "alice@example.com"},
    idempotency_key="create-user-alice-2024-01-15"
)

# ❌ 悪い: 汎用または再利用されるキー
await rmcp.call_tool(
    "create_user", 
    {...},
    idempotency_key="user"  # 汎用すぎ、競合を引き起こす
)
```

### 3. エラーハンドリング

```python
# ✅ 良い: 特定エラーハンドリング
try:
    result = await rmcp.call_tool("api_call", {})
except MCP-TxTimeoutError:
    # タイムアウトを特別に処理
    result = await rmcp.call_tool("api_call", {}, timeout_ms=60000)
except MCP-TxNetworkError:
    # ネットワーク問題を処理
    await asyncio.sleep(5)  # 待ってからリトライ
    result = await rmcp.call_tool("api_call", {})

# ❌ 悪い: 汎用エラーハンドリング
try:
    result = await rmcp.call_tool("api_call", {})
except Exception:
    pass  # 重要なエラー情報を隠す
```

### 4. 設定

```python
# ✅ 良い: 環境固有設定
if environment == "production":
    config = MCPTxConfig(
        default_timeout_ms=30000,
        retry_policy=RetryPolicy(max_attempts=5),
        max_concurrent_requests=20
    )
else:
    config = MCPTxConfig(
        default_timeout_ms=5000, 
        retry_policy=RetryPolicy(max_attempts=2),
        max_concurrent_requests=5
    )

rmcp = MCPTxSession(mcp_session, config)
```

---

**次へ**: [設定API](configuration_jp.md) →