# MCP-Tx信頼性機能

このドキュメントでは、MCP-Txが標準MCPに追加する信頼性機能について詳しく解説します。

## コア信頼性保証

### 1. ACK/NACK確認応答

MCP-Txはすべてのツール呼び出しに対して明示的な確認応答を要求します：

```python
result = await rmcp_session.call_tool("my_tool", {})

# 確認応答ステータスをチェック
if result.rmcp_meta.ack:
    print("ツールが受信を確認")
else:
    print(f"ツールが拒否: {result.rmcp_meta.error_message}")
```

**利点:**
- ツールが実際にリクエストを受信したかがわかる
- ネットワーク障害とツール拒否を区別
- デバッグ用の明確なエラーメッセージ

### 2. 指数バックオフ付き自動リトライ

MCP-Txは失敗した操作を自動的にリトライします：

```python
from mcp_tx import RetryPolicy

# リトライ動作を設定
retry_policy = RetryPolicy(
    max_attempts=5,
    base_delay_ms=1000,      # 1秒から開始
    backoff_multiplier=2.0,  # 毎回2倍に
    max_delay_ms=30000,      # 最大30秒まで
    jitter=True              # ランダム要素を追加
)

# 特定のツールに適用
result = await rmcp_session.call_tool(
    "unreliable_api",
    {"data": "important"},
    retry_policy=retry_policy
)

print(f"{result.rmcp_meta.attempts}回の試行で成功")
```

**リトライ対象:**
- ネットワークタイムアウト
- 接続エラー
- 5xxサーバーエラー
- 明示的なリトライ応答

**リトライ対象外:**
- 4xxクライアントエラー
- バリデーション失敗
- 認証エラー

### 3. リクエスト重複排除

冪等性キーで重複実行を防止：

```python
# 自動重複排除
result1 = await rmcp_session.call_tool(
    "create_user",
    {"email": "user@example.com"},
    idempotency_key="create-user-12345"
)

# 同じ呼び出しは再実行されない
result2 = await rmcp_session.call_tool(
    "create_user",
    {"email": "user@example.com"},
    idempotency_key="create-user-12345"
)

assert result2.rmcp_meta.duplicate == True
```

**重複排除ウィンドウ:**
- デフォルト: 5分
- セッション毎に設定可能
- サーバーサイドの状態管理

### 4. トランザクション追跡

マルチステップ操作の追跡：

```python
# 各リクエストが一意のIDを取得
result = await rmcp_session.call_tool("start_workflow", {})
request_id = result.rmcp_meta.request_id

# 相関のために使用
await rmcp_session.call_tool(
    "workflow_step_2",
    {"previous_step": request_id}
)
```

## FastMCPTxデコレータ機能

### ツールレベル設定

```python
from mcp_tx import FastMCPTx, RetryPolicy

app = FastMCPTx(mcp_session)

@app.tool(
    retry_policy=RetryPolicy(max_attempts=3),
    timeout_ms=10000,
    idempotency_key_generator=lambda args: f"process-{args['id']}"
)
async def process_data(id: str, data: dict) -> dict:
    """カスタム信頼性設定でデータを処理"""
    return {"processed": True, "id": id}
```

### 自動機能

FastMCPTxデコレータ使用時の自動機能：
- 入力検証
- 型チェック
- スレッドセーフ実行
- Deep Copy保護
- メモリ制限付きレジストリ

## 実装詳細

### プロトコルネゴシエーション

MCP-Tx機能は機能ネゴシエーションを通じて有効化：

```typescript
// クライアントがMCP-Txサポートを宣言
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "features": ["ack", "retry", "idempotency"]
      }
    }
  }
}
```

### メッセージ形式

MCP-Txは標準MCPメッセージを拡張：

```typescript
// MCP-Txメタデータ付きリクエスト
{
  "method": "tools/call",
  "params": {
    "name": "my_tool",
    "arguments": {},
    "_meta": {
      "rmcp": {
        "expect_ack": true,
        "request_id": "rmcp-123",
        "idempotency_key": "operation-456"
      }
    }
  }
}

// 保証付きレスポンス
{
  "result": {},
  "_meta": {
    "rmcp": {
      "ack": true,
      "processed": true,
      "duplicate": false,
      "attempts": 2
    }
  }
}
```

## ベストプラクティス

### 1. 適切なリトライポリシーの選択

```python
# 重要な操作 - 積極的リトライ
@app.tool(retry_policy=RetryPolicy(
    max_attempts=10,
    base_delay_ms=500
))
async def critical_operation(): ...

# ユーザー向け操作 - 高速失敗
@app.tool(retry_policy=RetryPolicy(
    max_attempts=2,
    base_delay_ms=1000
))
async def interactive_operation(): ...
```

### 2. 冪等な操作の設計

```python
# 良い例: 設計的に冪等
@app.tool()
async def set_user_status(user_id: str, status: str):
    # ステータス設定は自然に冪等
    await db.update_user(user_id, {"status": status})

# より良い例: 明示的な冪等性
@app.tool(
    idempotency_key_generator=lambda args: f"status-{args['user_id']}-{args['status']}"
)
async def update_user_status(user_id: str, status: str):
    # MCP-Txが重複更新を防止
    await db.update_user(user_id, {"status": status})
```

### 3. 信頼性メトリクスの監視

```python
# 本番環境での信頼性追跡
result = await app.call_tool("important_operation", data)

logger.info("操作完了", extra={
    "tool": "important_operation",
    "attempts": result.rmcp_meta.attempts,
    "was_duplicate": result.rmcp_meta.duplicate,
    "latency_ms": result.rmcp_meta.latency_ms
})
```

## 標準MCPとの比較

| 機能 | 標準MCP | MCP-Tx |
|---------|-------------|------|
| 配信保証 | ベストエフォート | ACK必須 |
| リトライロジック | クライアント実装 | 自動バックオフ |
| 重複防止 | クライアント実装 | 内蔵重複排除 |
| エラー可視性 | 基本エラー | 詳細な失敗理由 |
| トランザクション追跡 | 手動 | 自動リクエストID |

## 関連ドキュメント

- [アーキテクチャ概要](architecture_jp.md) - MCP-TxがMCPを強化する方法
- [はじめに](getting-started_jp.md) - クイックスタートガイド
- [API リファレンス](api/rmcp-session_jp.md) - 詳細なAPI仕様

---

**前へ**: [アーキテクチャ](architecture_jp.md) | **次へ**: [設定ガイド](configuration_jp.md)