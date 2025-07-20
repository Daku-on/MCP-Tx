# MCP-Tx (Model Context Protocol with Transactions) - 完全ドキュメント

**バージョン**: 0.1.0 (本番対応MVP)  
**最終更新**: 2025年1月  
**言語**: 日本語

---

## 目次

1. [はじめに](#はじめに)
2. [始め方](#始め方)
3. [アーキテクチャ概要](#アーキテクチャ概要)
4. [互換性ガイド](#互換性ガイド)
5. [設定リファレンス](#設定リファレンス)
6. [信頼性機能](#信頼性機能)
7. [パフォーマンス最適化](#パフォーマンス最適化)
8. [MCPからの移行](#mcpからの移行)
9. [AIエージェント構築](#aiエージェント構築)
10. [APIリファレンス](#apiリファレンス)
11. [使用例](#使用例)
    - [基本例](#基本例)
    - [高度な例](#高度な例)
    - [統合例](#統合例)
12. [FAQ](#faq)
13. [トラブルシューティング](#トラブルシューティング)

---

## はじめに

# MCP-Tx ドキュメント

MCP-Tx の完全なドキュメント

## MCP-Txとは？

**MCP-Tx (Reliable Model Context Protocol)** は、既存のMCPセッションに信頼性レイヤーを提供するPythonライブラリです。配信保証、自動リトライ、リクエスト重複排除、トランザクション追跡を追加しながら、既存のMCPサーバーとの100%後方互換性を維持します。

## 主な機能

- ✅ **配信保証** - ACK/NACKメカニズム
- ✅ **自動リトライ** - 指数バックオフとジッター
- ✅ **冪等性** - 重複実行の防止
- ✅ **リッチなエラーハンドリング** - 詳細なコンテキスト付き
- ✅ **リクエスト追跡** - トランザクションライフサイクル管理
- ✅ **100%後方互換性** - 既存のMCPサーバーで動作

## クイックスタート

```python
from mcp_tx import MCPTxSession
from mcp.client.session import ClientSession

# 既存のMCPセッションをラップ
mcp_session = ClientSession(...)
mcp_tx_session = MCPTxSession(mcp_session)

await mcp_tx_session.initialize()

# 信頼性保証付きツール呼び出し
result = await mcp_tx_session.call_tool("file_reader", {"path": "/data.txt"})

if result.ack:
    print(f"成功: {result.result}")
    print(f"試行回数: {result.attempts}")
else:
    print(f"失敗: {result.mcp_tx_meta.error_message}")
```

## ドキュメント構造

### 📖 コアドキュメント

| ドキュメント | 説明 | 対象 |
|-------------|------|------|
| [**はじめる**](#始め方) | 5分でMCP-Txを始める | 新規ユーザー |
| [**アーキテクチャ**](#アーキテクチャ概要) | 技術的な深掘り | 開発者 |
| [**信頼性機能**](#信頼性機能) | ACK/NACK、リトライ、冪等性 | 開発者 |
| [**設定ガイド**](#設定リファレンス) | 詳細設定オプション | 開発者・運用 |
| [**パフォーマンス**](#パフォーマンス最適化) | 本番最適化ガイド | 運用チーム |
| [**移行ガイド**](#mcpからの移行) | MCPからMCP-Txへの移行 | 既存ユーザー |
| [**互換性**](#互換性ガイド) | バージョン・プラットフォーム対応 | すべて |
| [**FAQ**](#faq) | よくある質問と回答 | すべて |
| [**トラブルシューティング**](#トラブルシューティング) | 問題解決ガイド | 運用チーム |

### 📋 APIリファレンス

| API | 説明 |
|-----|------|
| [**MCPTxSession**](#apiリファレンス) | メインインターフェース |

### 💡 実用的な例

| 例 | 説明 |
|----|------|
| [**基本的な使用方法**](#基本例) | 一般的な使用パターン |
| [**AIエージェント**](#aiエージェント構築) | MCP-Txで信頼性の高いAIエージェント構築 |
| [**高度な例**](#高度な例) | 複雑なワークフローと統合 |
| [**フレームワーク統合**](#統合例) | Django、Flask、Celery統合 |

## 使用シナリオ

### 🔄 信頼性が重要な操作
```python
# ファイル処理 - 冪等性保証
result = await mcp_tx_session.call_tool(
    "file_processor",
    {"path": "/critical_data.csv", "operation": "validate"},
    idempotency_key="validate-critical-2024-01-15"
)
```

### 🌐 外部API呼び出し
```python
# カスタムリトライポリシー付きAPI呼び出し
api_retry = RetryPolicy(max_attempts=5, base_delay_ms=1000)
result = await mcp_tx_session.call_tool(
    "http_client", 
    {"url": "https://api.example.com/data"},
    retry_policy=api_retry,
    timeout_ms=30000
)
```

### ⚡ 高負荷システム
```python
# 並行制御付き設定
config = MCPTxConfig(
    max_concurrent_requests=20,
    default_timeout_ms=15000
)
mcp_tx_session = MCPTxSession(mcp_session, config)
```

## パフォーマンス概要

| メトリック | 標準MCP | MCP-Tx | オーバーヘッド |
|------------|---------|------|-------------|
| **レイテンシ** | ベースライン | +2-5% | < 1ms |
| **メモリ** | ベースライン | +10-100KB | リクエスト追跡 |
| **ネットワーク** | ベースライン | +200-500バイト | MCP-Txメタデータ |
| **スループット** | ベースライン | 同等 | 最小限の影響 |

## インストール

```bash
# uv（推奨）
uv add mcp_tx

# pip
pip install mcp_tx
```

## 要件

- **Python**: 3.10+
- **依存関係**: `anyio`, `mcp` (既存のMCPライブラリ)
- **互換性**: すべてのMCPサーバー（MCP-Tx対応・非対応問わず）

## サポート

### 🆘 ヘルプが必要ですか？

1. **[トラブルシューティングガイド](#トラブルシューティング)** をチェック
2. **[FAQ](#faq)** で一般的な質問を確認
3. **[GitHub Issues](https://github.com/Daku-on/MCP-Tx/issues)** で問題を報告

### 📚 詳細情報

- **初心者**: [はじめる](#始め方) から開始
- **開発者**: [アーキテクチャ](#アーキテクチャ概要) で技術詳細を確認
- **既存ユーザー**: [移行ガイド](#mcpからの移行) でアップグレード方法を確認

---

## 始め方

# はじめる

5分でMCP-Tx (MCP-Tx (Reliable Model Context Protocol)) の使用を開始しましょう。

## インストール

```bash
# uv（推奨）
uv add mcp_tx

# pip
pip install mcp_tx

# インストール確認
python -c "import mcp_tx; print(f'MCP-Tx {mcp_tx.__version__} installed')"
```

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
print(f"承認済み: {result.ack}")           # リクエストが承認されたか
print(f"処理済み: {result.processed}")      # ツールが実際に実行されたか
print(f"試行回数: {result.attempts}")       # リトライ回数
print(f"ステータス: {result.final_status}") # 'completed' または 'failed'

# 実際の結果にアクセス
if result.ack:
    actual_result = result.result
    print(f"ファイル内容: {actual_result}")
```

## 実用的な例

### ファイル操作の信頼性

```python
async def reliable_file_operations():
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        # 冪等性付きファイル書き込み
        write_result = await mcp_tx.call_tool(
            "file_writer",
            {
                "path": "/output/report.txt",
                "content": "処理完了: データ分析結果"
            },
            idempotency_key="report-2024-01-15-v1"
        )
        
        if write_result.ack:
            print("✅ ファイル書き込み成功")
        
        # 自動リトライ付きファイル読み込み
        read_result = await mcp_tx.call_tool(
            "file_reader",
            {"path": "/output/report.txt"},
            timeout_ms=10000  # 10秒タイムアウト
        )
        
        if read_result.ack:
            print(f"📄 ファイル内容: {read_result.result['content']}")
```

### API呼び出しの信頼性

```python
from mcp_tx import RetryPolicy

async def reliable_api_calls():
    # API用のカスタムリトライポリシー
    api_retry = RetryPolicy(
        max_attempts=5,           # 最大5回試行
        base_delay_ms=1000,       # 1秒から開始
        backoff_multiplier=2.0,   # 指数バックオフ: 1s, 2s, 4s, 8s, 16s
        jitter=True,              # ランダムジッターを追加
        retryable_errors=[
            "CONNECTION_ERROR", "TIMEOUT", "RATE_LIMITED"
        ]
    )
    
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        result = await mcp_tx.call_tool(
            "http_client",
            {
                "method": "GET",
                "url": "https://api.example.com/users",
                "headers": {"Authorization": f"Bearer {os.environ['API_TOKEN']}"}
            },
            retry_policy=api_retry,
            timeout_ms=30000  # 30秒タイムアウト
        )
        
        if result.ack:
            users = result.result
            print(f"👥 {len(users)} ユーザーを取得")
        else:
            print(f"❌ API呼び出し失敗: {result.mcp_tx_meta.error_message}")
```

## 設定のカスタマイズ

### 環境固有の設定

```python
from mcp_tx import MCPTxConfig, RetryPolicy
import os

def create_config():
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return MCPTxConfig(
            default_timeout_ms=30000,      # 30秒
            retry_policy=RetryPolicy(
                max_attempts=5,
                base_delay_ms=2000,         # 2秒から開始
                backoff_multiplier=2.0
            ),
            max_concurrent_requests=20,    # 高い並行性
            deduplication_window_ms=600000 # 10分間の重複排除
        )
    else:
        return MCPTxConfig(
            default_timeout_ms=5000,       # 5秒（開発用）
            retry_policy=RetryPolicy(
                max_attempts=2,
                base_delay_ms=500           # 0.5秒から開始
            ),
            max_concurrent_requests=5      # 開発環境では低めに
        )

# 設定を使用
config = create_config()
mcp_tx_session = MCPTxSession(mcp_session, config)
```

### 操作別設定

```python
async def operation_specific_config():
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        # 高速操作 - 短いタイムアウト
        cache_result = await mcp_tx.call_tool(
            "cache_lookup",
            {"key": "user_123"},
            timeout_ms=2000  # 2秒
        )
        
        # 低速操作 - 長いタイムアウト
        ml_result = await mcp_tx.call_tool(
            "ml_inference",
            {"model": "large_language_model", "input": "データ"},
            timeout_ms=300000  # 5分
        )
        
        # 重要な操作 - 積極的リトライ
        critical_retry = RetryPolicy(max_attempts=10, base_delay_ms=500)
        backup_result = await mcp_tx.call_tool(
            "database_backup",
            {"target": "s3://backup-bucket"},
            retry_policy=critical_retry
        )
```

## エラーハンドリング

### 特定エラータイプの処理

```python
from mcp_tx.types import MCPTxTimeoutError, MCPTxNetworkError

async def robust_error_handling():
    try:
        result = await mcp_tx_session.call_tool("external_service", {})
        
        if result.ack:
            return result.result
        else:
            print(f"ツール実行失敗: {result.mcp_tx_meta.error_message}")
            
    except MCPTxTimeoutError as e:
        print(f"タイムアウト: {e.details['timeout_ms']}ms後")
        # より長いタイムアウトで再試行
        return await mcp_tx_session.call_tool(
            "external_service", {}, timeout_ms=60000
        )
        
    except MCPTxNetworkError as e:
        print(f"ネットワークエラー: {e.message}")
        # しばらく待ってから再試行
        await asyncio.sleep(5)
        return await mcp_tx_session.call_tool("external_service", {})
```

## 並行処理

### 複数操作の並列実行

```python
import asyncio

async def concurrent_operations():
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        # 複数のファイルを並列処理
        files = ["/data/file1.txt", "/data/file2.txt", "/data/file3.txt"]
        
        async def process_file(file_path):
            return await mcp_tx.call_tool(
                "file_processor",
                {"path": file_path, "operation": "analyze"},
                idempotency_key=f"analyze-{file_path.replace('/', '_')}"
            )
        
        # 並列実行
        tasks = [process_file(file_path) for file_path in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果処理
        successful = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ {files[i]} 処理失敗: {result}")
            elif result.ack:
                successful += 1
                print(f"✅ {files[i]} 処理成功")
        
        print(f"📊 {successful}/{len(files)} ファイル処理完了")
```

## デバッグとモニタリング

### ログ有効化

```python
import logging

# MCP-Tx内部のデバッグログを有効化
logging.basicConfig(level=logging.DEBUG)
mcp_tx_logger = logging.getLogger("mcp_tx")
mcp_tx_logger.setLevel(logging.DEBUG)

# これでMCP-Txが以下をログ出力します:
# - リクエストID生成
# - リトライ試行と遅延
# - キャッシュヒット/ミス
# - サーバー機能ネゴシエーション
# - エラー詳細
```

### セッション状態監視

```python
async def monitor_session():
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        print(f"MCP-Tx有効: {mcp_tx.mcp_tx_enabled}")
        print(f"アクティブリクエスト: {len(mcp_tx.active_requests)}")
        
        # 操作実行
        result = await mcp_tx.call_tool("test", {})
        
        print(f"試行回数: {result.attempts}")
        print(f"最終ステータス: {result.final_status}")
```

## よくある使用パターン

### パターン 1: ドロップイン置換

```python
# 前: 標準MCP
# result = await mcp_session.call_tool("tool", args)

# 後: MCP-Tx（信頼性機能付き）
result = await mcp_tx_session.call_tool("tool", args)
if result.ack:
    actual_result = result.result  # 元のMCP結果
```

### パターン 2: 条件付きMCP-Tx使用

```python
USE_MCP_TX = os.getenv("USE_MCP_TX", "false").lower() == "true"

if USE_MCP_TX:
    session = MCPTxSession(mcp_session)
    await session.initialize()
else:
    session = mcp_session

# セッションを通常通り使用
result = await session.call_tool("tool", args)

# MCP-Tx結果の場合は適切に処理
if hasattr(result, 'ack'):
    actual_result = result.result if result.ack else None
else:
    actual_result = result
```

### パターン 3: バッチ処理

```python
async def batch_processing(items):
    results = []
    failed = []
    
    async with MCPTxSession(mcp_session) as mcp_tx:
        await mcp_tx.initialize()
        
        for item in items:
            try:
                result = await mcp_tx.call_tool(
                    "item_processor",
                    {"item": item},
                    idempotency_key=f"process-{item['id']}"
                )
                
                if result.ack:
                    results.append(result.result)
                else:
                    failed.append((item, result.mcp_tx_meta.error_message))
                    
            except Exception as e:
                failed.append((item, str(e)))
    
    print(f"✅ 成功: {len(results)}, ❌ 失敗: {len(failed)}")
    return results, failed
```

## 次のステップ

### 📚 さらに学ぶ

- **[アーキテクチャ](#アーキテクチャ概要)** - MCP-Txの内部動作を理解
- **[移行ガイド](#mcpからの移行)** - 既存のMCPコードをアップグレード
- **[FAQ](#faq)** - よくある質問と回答

### 🔧 詳細設定

- **[APIリファレンス](#apiリファレンス)** - 完全なAPIドキュメント
- **[例集](#基本例)** - より多くの実用例

### 🆘 サポート

- **[トラブルシューティング](#トラブルシューティング)** - 問題解決ガイド
- **[GitHub Issues](https://github.com/Daku-on/MCP-Tx/issues)** - バグ報告・機能要求

---

## アーキテクチャ概要

# MCP-Txアーキテクチャ概要

MCP-TxがどのようにMCPに信頼性保証を追加するかを理解する。

## ハイレベルアーキテクチャ

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│                 │    │                      │    │                 │
│  クライアント   │    │    MCP-Txセッション    │    │   MCPサーバー   │
│  アプリケーション│    │   (信頼性ラッパー)    │    │   (既存)        │
│                 │    │                      │    │                 │
└─────────────────┘    └──────────────────────┘    └─────────────────┘
         │                        │                          │
         │ call_tool()            │ 拡張MCP                  │ 標準MCP  
         ├─────────────────────▶  │ _meta.mcp_tx付き          ├──────────────▶
         │                        │                          │
         │ MCPTxResult             │ 標準MCP                  │ ツール結果
         ◀─────────────────────── │ レスポンス               ◀──────────────┤
         │                        │                          │
```

## コアコンポーネント

### 1. MCPTxSession（ラッパー）

既存のMCPセッションをラップするメインインターフェース：

```python
class MCPTxSession:
    def __init__(self, mcp_session: BaseSession, config: MCPTxConfig = None):
        self.mcp_session = mcp_session  # 既存のMCPセッション
        self.config = config or MCPTxConfig()
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

MCP-Txは標準MCPメッセージを信頼性メタデータで拡張：

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
    "_meta": {"mcp_tx": {"expect_ack": True, ...}},
    ...
}

# サーバーが処理してACKで応答
response = {
    "result": {...},
    "_meta": {
        "mcp_tx": {
            "ack": True,           # 明示的な承認
            "processed": True,     # ツールが実行された
            "request_id": "...",   # 関連付け
        }
    }
}

# クライアントがACKを検証してMCPTxResultを返す
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
class MCPTxSession:
    def __init__(self):
        # メモリ安全性のためのTTL付きLRUキャッシュ
        self._deduplication_cache: dict[str, tuple[MCPTxResult, datetime]] = {}
    
    def _get_cached_result(self, idempotency_key: str) -> MCPTxResult | None:
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
class MCPTxSession:
    def __init__(self, config: MCPTxConfig):
        # 並行性制御用セマフォ
        self._request_semaphore = anyio.Semaphore(config.max_concurrent_requests)
        
        # アクティブリクエスト追跡
        self._active_requests: dict[str, RequestTracker] = {}
    
    async def call_tool(self, ...):
        # 処理前にセマフォを取得
        async with self._request_semaphore:
            return await self._call_tool_with_retry(...)
```

---

*[注: 長さの制約により、完全なドキュメントは複数のレスポンスに分割されます。残りのセクション（互換性ガイド、設定リファレンス、信頼性機能、パフォーマンス最適化、移行ガイド、AIエージェント、APIリファレンス、使用例、FAQ、トラブルシューティング）は、完全なカバレッジのために続きます。]*

---

**これは完全な日本語ドキュメントのパート1です。ドキュメントは完全なカバレッジのために追加セクションと続きます。**