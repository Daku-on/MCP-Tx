# MCP-Tx ドキュメント

MCP-Tx (Reliable Model Context Protocol) は、既存のMCPセッションに信頼性レイヤーを提供するPythonライブラリです。

## インストール

```bash
# uv（推奨）
uv add rmcp

# pip
pip install rmcp
```

## クイックスタート

```python
from mcp_tx import MCP_TxSession
from mcp.client.session import ClientSession

# 既存のMCPセッションをラップ
mcp_session = ClientSession(...)
mcp_tx_session = MCP_TxSession(mcp_session)

await mcp_tx_session.initialize()

# 信頼性保証付きツール呼び出し
result = await mcp_tx_session.call_tool("file_reader", {"path": "/data.txt"})

if result.ack:
    print(f"成功: {result.result}")
    print(f"試行回数: {result.attempts}")
else:
    print(f"失敗: {result.mcp_tx_meta.error_message}")
```

# はじめる

## 基本的な使用方法

### ステップ 1: 既存のMCPセッションをラップ

```python
import asyncio
import os
from mcp_tx import MCPTxSession
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport

async def main():
    # 既存のMCPセットアップ
    transport = StdioClientTransport(...)
    mcp_session = ClientSession(transport)
    
    # MCP-Txで信頼性機能を追加
    mcp_tx_session = MCPTxSession(mcp_session)
    
    # 初期化（必須）
    await mcp_tx_session.initialize()
    
    # これで信頼性保証付きツール呼び出しが可能
    result = await mcp_tx_session.call_tool("echo", {"message": "Hello MCP-Tx!"})
    
    if result.ack:
        print(f"成功: {result.result}")
    else:
        print(f"失敗: {result.mcp_tx_meta.error_message}")
    
    await mcp_tx_session.close()

asyncio.run(main())
```

### ステップ 2: 結果の理解

```python
result = await mcp_tx_session.call_tool("file_reader", {"path": "/data.txt"})

# MCP-Txの保証をチェック
print(f"承認済み: {result.ack}")
print(f"処理済み: {result.processed}")
print(f"試行回数: {result.attempts}")
print(f"ステータス: {result.final_status}")

# 実際の結果にアクセス
if result.ack:
    actual_result = result.result
    print(f"ファイル内容: {actual_result}")
```

# アーキテクチャ

### MCPTxSession（ラッパー）

```python
class MCPTxSession:
    def __init__(self, mcp_session: BaseSession, config: MCPTxConfig = None):
        self.mcp_session = mcp_session
        self.config = config or MCPTxConfig()
```

### メッセージ拡張

```json
{
  "method": "tools/call",
  "params": {
    "name": "file_reader",
    "arguments": {"path": "/data.txt"},
    "_meta": {
      "mcp_tx": {
        "version": "0.1.0",
        "request_id": "550e8400-e29b-41d4-a716-446655440000",
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

# 信頼性機能

## コア信頼性保証

### ACK/NACK確認応答

```python
result = await mcp_tx_session.call_tool("my_tool", {})
if result.mcp_tx_meta.ack:
    print("ツールが受信を確認")
else:
    print(f"ツールが拒否: {result.mcp_tx_meta.error_message}")
```

### 指数バックオフ付き自動リトライ

```python
from mcp_tx import RetryPolicy
retry_policy = RetryPolicy(
    max_attempts=5,
    base_delay_ms=1000,
    backoff_multiplier=2.0,
    jitter=True
)
result = await mcp_tx_session.call_tool(
    "unreliable_api",
    {"data": "important"},
    retry_policy=retry_policy
)
```

### リクエスト重複排除

```python
result = await mcp_tx_session.call_tool(
    "create_user",
    {"email": "user@example.com"},
    idempotency_key="create-user-12345"
)
```

# 設定ガイド

## クイックスタート設定

### 基本セットアップ

```python
from mcp_tx import MCPTxConfig, MCPTxSession
config = MCPTxConfig()
session = MCPTxSession(mcp_session, config)
```

### 一般的なカスタマイズ

```python
from mcp_tx import MCPTxConfig, RetryPolicy
config = MCPTxConfig(
    default_timeout_ms=30000,
    max_concurrent_requests=10,
    deduplication_window_ms=300000,
    retry_policy=RetryPolicy(
        max_attempts=3,
        base_delay_ms=1000,
        backoff_multiplier=2.0
    ),
    enable_request_logging=True,
    log_level="INFO"
)
```

# APIリファレンス

## クラス: MCPTxSession

### コンストラクタ
`__init__(self, mcp_session: BaseSession, config: MCPTxConfig | None = None)`

### メソッド
- `initialize(self, **kwargs) -> Any`
- `call_tool(self, name: str, arguments: dict, *, idempotency_key: str | None = None, timeout_ms: int | None = None, retry_policy: RetryPolicy | None = None) -> MCPTxResult`
- `close(self) -> None`

### プロパティ
- `mcp_tx_enabled: bool`
- `active_requests: dict[str, RequestTracker]`

## データクラス: MCPTxResult
- `result: Any`
- `mcp_tx_meta: MCPTxResponse`

# 使用例

## 基本的な使用例

### ファイル操作とAPI呼び出し

```python
# 冪等性付きファイル書き込み
write_result = await mcp_tx.call_tool(
    "file_writer",
    {"path": "/output/report.txt", "content": "..."},
    idempotency_key="report-2024-01-15-v1"
)

# 自動リトライ付きAPI呼び出し
read_result = await mcp_tx.call_tool(
    "http_client",
    {"method": "GET", "url": "https://api.example.com/users"},
    timeout_ms=10000
)
```

## 高度な使用例

### マルチステップワークフローとサーキットブレーカー

```python
# 複数の信頼性機能を組み合わせたワークフロー
class WorkflowManager:
    async def execute_data_pipeline(self, source_url: str):
        # ... ステップ1: ダウンロード (リトライ付き)
        # ... ステップ2: 検証
        # ... ステップ3: 処理 (カスタムリトライポリシー)
        # ... ステップ4: アップロード
        pass

# サーキットブレーカーで保護された呼び出し
breaker = CircuitBreaker()
@app.tool()
async def protected_api_call(endpoint: str):
    return await breaker.call(external_api_call, endpoint)
```

## フレームワーク統合

### FastAPI, Django, Celery との連携

```python
# FastAPI
@app.post("/process")
async def process_file(mcp_tx: MCPTxSession = Depends(get_mcp_tx_session)):
    result = await mcp_tx.call_tool(...)

# Django (async_to_syncを使用)
result = async_to_sync(request.rmcp.call_tool)(...)

# Celery (カスタムタスククラス)
@app.task(base=MCP-TxTask)
def process_data_async(self, data_id: str):
    result = loop.run_until_complete(self.rmcp.call_tool(...))
```

## AIエージェントの構築

信頼性の高いAIエージェントを構築するために、リトライ、冪等性、トランザクション追跡などのMCP-Tx機能を活用します。

```python
# スマートリサーチアシスタントの例
class SmartResearchAssistant:
    async def conduct_research(self, query: str):
        # ステップ1: Web検索 (リトライ付き)
        # ステップ2: コンテンツ分析 (冪等性)
        # ステップ3: ファクトチェック
        # ステップ4: レポート生成
        # ステップ5: 結果を保存
        pass
```

# 移行ガイド

## MCPからMCP-Txへの移行戦略

### ドロップイン置換

**移行前 (MCP):**
```python
result = await session.call_tool("file_reader", {"path": "/data.txt"})
```

**移行後 (MCP-Tx):**
```python
mcp_tx_session = MCPTxSession(mcp_session)
await mcp_tx_session.initialize()
result = await mcp_tx_session.call_tool("file_reader", {"path": "/data.txt"})
if result.ack:
    actual_result = result.result
```

# よくある質問 (FAQ)

### MCP-Txとは何ですか？
既存のMCPセッションに信頼性機能を追加する後方互換性のあるレイヤーです。

### MCPサーバーの修正は必要ですか？
いいえ。MCP-Txはクライアントサイドで動作し、標準的なMCPサーバーと互換性があります。

### 既存のMCPライブラリで使えますか？
はい。MCPセッションインターフェースを実装した任意のオブジェクトをラップできます。
