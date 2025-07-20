# MCPからMCP-Txへの移行

標準MCPからMCP-Txへ信頼性保証付きでアップグレードするためのステップバイステップガイド。

## 移行する理由

**標準MCPの制限**：
- ❌ 配信保証なし（ファイア・アンド・フォーゲット）
- ❌ 失敗時の自動リトライなし
- ❌ 重複リクエスト保護なし
- ❌ 限定的なエラーハンドリングと復旧
- ❌ リクエストライフサイクルの可視性なし

**MCP-Txの利点**：
- ✅ **配信保証** ACK/NACK付き
- ✅ **自動リトライ** 指数バックオフ付き
- ✅ **冪等性** 重複実行を防ぐ
- ✅ **リッチなエラーハンドリング** 詳細なコンテキスト付き
- ✅ **リクエスト追跡** とトランザクションサポート
- ✅ **100%後方互換性** 既存のMCPサーバーで動作

## 移行戦略

### 戦略 1: ドロップイン置換（推奨）

**最適な用途**: 最小限のコード変更で即座に信頼性の恩恵を受けたいアプリケーション。

#### 移行前（標準MCP）
```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport

async def mcp_example():
    # 標準MCPセットアップ
    transport = StdioClientTransport(...)
    session = ClientSession(transport)
    
    await session.initialize()
    
    # 標準ツール呼び出し - 保証なし
    try:
        result = await session.call_tool("file_reader", {"path": "/data.txt"})
        print(f"結果: {result}")
    except Exception as e:
        print(f"エラー: {e}")
        # 手動リトライロジックが必要
    
    await session.close()
```

#### 移行後（MCP-Txラッパー）
```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport
from rmcp import MCP-TxSession  # MCP-Txインポート追加

async def rmcp_example():
    # 同じMCPセットアップ
    transport = StdioClientTransport(...)
    mcp_session = ClientSession(transport)
    
    # 信頼性のためにMCP-Txでラップ
    rmcp_session = MCP-TxSession(mcp_session)
    
    await rmcp_session.initialize()  # 同じインターフェース
    
    # 保証付き拡張ツール呼び出し
    result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})
    
    # 豊富な信頼性情報
    print(f"承認済み: {result.ack}")
    print(f"処理済み: {result.processed}")
    print(f"試行回数: {result.attempts}")
    print(f"ステータス: {result.final_status}")
    
    if result.ack:
        print(f"結果: {result.result}")
    else:
        print(f"失敗: {result.rmcp_meta.error_message}")
    
    await rmcp_session.close()
```

**移行ステップ**：
1. ✅ MCP-Txをインストール: `uv add mcp_tx`
2. ✅ MCP-TxSessionをインポート: `from rmcp import MCP-TxSession`
3. ✅ MCPセッションをラップ: `rmcp_session = MCP-TxSession(mcp_session)`
4. ✅ 結果処理を更新: `result.ack`と`result.result`を使用
5. ✅ 既存サーバーでテスト（MCP-Tx未サポート時自動フォールバック）

### 戦略 2: 段階的拡張

**最適な用途**: MCP-Tx機能を段階的に追加したい大規模アプリケーション。

#### フェーズ 1: 基本ラッパー
```python
class ApplicationClient:
    def __init__(self, mcp_session):
        # フェーズ1: 基本MCP-Txでラップ
        self.session = MCP-TxSession(mcp_session)
        self.initialized = False
    
    async def initialize(self):
        await self.session.initialize()
        self.initialized = True
    
    async def read_file(self, path: str) -> str:
        """フェーズ1: 基本信頼性"""
        if not self.initialized:
            raise RuntimeError("クライアント未初期化")
        
        result = await self.session.call_tool("file_reader", {"path": path})
        
        if not result.ack:
            raise RuntimeError(f"ファイル読み込み失敗: {result.rmcp_meta.error_message}")
        
        return result.result["content"]
```

#### フェーズ 2: 冪等性追加
```python
    async def write_file(self, path: str, content: str) -> bool:
        """フェーズ2: 書き込み操作に冪等性を追加"""
        import hashlib
        
        # 決定的な冪等性キーを作成
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        idempotency_key = f"write-{path.replace('/', '_')}-{content_hash}"
        
        result = await self.session.call_tool(
            "file_writer",
            {"path": path, "content": content},
            idempotency_key=idempotency_key
        )
        
        return result.ack
```

#### フェーズ 3: カスタムリトライポリシー
```python
    async def api_call(self, endpoint: str, data: dict = None) -> dict:
        """フェーズ3: 外部API用カスタムリトライ"""
        from rmcp import RetryPolicy
        
        # 外部API用積極的リトライ
        api_retry = RetryPolicy(
            max_attempts=5,
            base_delay_ms=1000,
            backoff_multiplier=2.0,
            jitter=True,
            retryable_errors=["CONNECTION_ERROR", "TIMEOUT", "RATE_LIMITED"]
        )
        
        result = await self.session.call_tool(
            "http_client",
            {"endpoint": endpoint, "data": data},
            retry_policy=api_retry,
            timeout_ms=30000
        )
        
        if not result.ack:
            raise RuntimeError(f"API呼び出し失敗: {result.rmcp_meta.error_message}")
        
        return result.result
```

### 戦略 3: フィーチャーフラグアプローチ

**最適な用途**: ロールバック機能付き段階的展開が必要な本番システム。

```python
import os
from typing import Union
from mcp.client.session import ClientSession
from rmcp import MCP-TxSession

class ConfigurableClient:
    def __init__(self, mcp_session: ClientSession):
        self.mcp_session = mcp_session
        
        # MCP-Txのフィーチャーフラグ
        use_rmcp = os.getenv("USE_MCP-Tx", "false").lower() == "true"
        
        if use_rmcp:
            print("🚀 拡張信頼性のためMCP-Txを使用")
            self.session = MCP-TxSession(mcp_session)
        else:
            print("📡 標準MCPを使用")
            self.session = mcp_session
        
        self.is_rmcp = isinstance(self.session, MCP-TxSession)
    
    async def call_tool_with_fallback(self, name: str, arguments: dict) -> dict:
        """MCP-Tx利用可能時使用、MCPエラーハンドリングにフォールバック"""
        
        if self.is_rmcp:
            # MCP-Txパス - リッチエラーハンドリング
            result = await self.session.call_tool(name, arguments)
            
            if result.ack:
                return {
                    "success": True,
                    "data": result.result,
                    "metadata": {
                        "attempts": result.attempts,
                        "status": result.final_status
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.rmcp_meta.error_message,
                    "attempts": result.attempts
                }
        else:
            # 標準MCPパス - 基本エラーハンドリング
            try:
                result = await self.session.call_tool(name, arguments)
                return {
                    "success": True,
                    "data": result,
                    "metadata": {"attempts": 1}
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "attempts": 1
                }
```

## 一般的な移行パターン

### 1. エラーハンドリングの移行

#### 移行前（MCP）
```python
# 手動リトライ付き基本try-catch
async def unreliable_operation():
    max_retries = 3
    delay = 1.0
    
    for attempt in range(max_retries):
        try:
            result = await mcp_session.call_tool("unreliable_api", {})
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # 手動指数バックオフ
            else:
                raise e
```

#### 移行後（MCP-Tx）
```python
# リッチエラーハンドリング付き自動リトライ
async def unreliable_operation():
    from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError
    
    try:
        result = await rmcp_session.call_tool("unreliable_api", {})
        return result.result if result.ack else None
    except MCP-TxTimeoutError as e:
        print(f"操作が{e.details['timeout_ms']}ms後にタイムアウト")
        return None
    except MCP-TxNetworkError as e:
        print(f"ネットワークエラー: {e.message}")
        return None
```

### 2. 冪等性の移行

#### 移行前（MCP）
```python
# 手動重複検出
processed_operations = set()

async def idempotent_operation(operation_id: str, data: dict):
    if operation_id in processed_operations:
        print(f"操作{operation_id}は既に処理済み")
        return
    
    try:
        result = await mcp_session.call_tool("processor", {"id": operation_id, "data": data})
        processed_operations.add(operation_id)
        return result
    except Exception as e:
        # 失敗時は処理済みとしてマークしない
        raise e
```

#### 移行後（MCP-Tx）
```python
# 自動重複検出
async def idempotent_operation(operation_id: str, data: dict):
    result = await rmcp_session.call_tool(
        "processor",
        {"id": operation_id, "data": data},
        idempotency_key=f"process-{operation_id}"
    )
    
    if result.rmcp_meta.duplicate:
        print(f"操作{operation_id}は既に処理済み")
    
    return result.result if result.ack else None
```

### 3. 設定の移行

#### 移行前（MCP）
```python
# アプリケーションレベル設定
class MCPClient:
    def __init__(self):
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # 信頼性機能の手動実装
```

#### 移行後（MCP-Tx）
```python
# 宣言的MCP-Tx設定
from rmcp import MCP-TxConfig, RetryPolicy

class MCP-TxClient:
    def __init__(self):
        config = MCP-TxConfig(
            default_timeout_ms=30000,
            retry_policy=RetryPolicy(
                max_attempts=3,
                base_delay_ms=1000,
                backoff_multiplier=2.0,
                jitter=True
            ),
            max_concurrent_requests=10,
            deduplication_window_ms=300000
        )
        
        self.session = MCP-TxSession(mcp_session, config)
        # 信頼性機能は自動処理
```

## 移行チェックリスト

### 移行前評価

- [ ] **MCP使用状況の棚卸**: コードベース内のすべての`call_tool()`呼び出しをドキュメント化
- [ ] **重要操作の特定**: 信頼性保証が必要な操作をマーク
- [ ] **エラーハンドリングの確認**: 現在のエラーハンドリングパターンをドキュメント化
- [ ] **MCPサーバーバージョン確認**: MCP-Txとの互換性を確認
- [ ] **テスト戦略の計画**: 移行検証用テストシナリオを定義

### 移行実行

- [ ] **MCP-Txインストール**: `uv add mcp_tx`
- [ ] **インポート更新**: `from rmcp import MCP-TxSession`を追加
- [ ] **MCPセッションラップ**: 直接MCP使用をMCP-Txラッパーに置換
- [ ] **結果処理更新**: `result.ack`と`result.result`パターンを使用
- [ ] **MCP-Tx設定**: 適切なタイムアウト、リトライポリシー、並行性制限を設定
- [ ] **冪等性キー追加**: 冪等であるべき操作用
- [ ] **エラーハンドリング拡張**: MCP-Tx固有例外タイプを使用

### 移行後検証

- [ ] **後方互換性テスト**: 非MCP-Txサーバーで動作確認
- [ ] **信頼性機能検証**: リトライ、冪等性、タイムアウトハンドリングをテスト
- [ ] **パフォーマンステスト**: 標準MCPとのMCP-Txオーバーヘッドを測定
- [ ] **エラー率監視**: 移行前後のエラー率を比較
- [ ] **ドキュメント更新**: 新しいMCP-Tx固有機能をドキュメント化

## 移行問題のトラブルシューティング

### 問題: インポートエラー

```python
# ❌ 問題
from rmcp import MCP-TxSession  # ModuleNotFoundError

# ✅ 解決  
# 最初にMCP-Txをインストール
# uv add mcp_tx
# または pip install mcp_tx
```

### 問題: 結果アクセスエラー

```python
# ❌ 問題
result = await rmcp_session.call_tool("test", {})
print(result)  # MCP-TxResultオブジェクト、直接結果ではない

# ✅ 解決
result = await rmcp_session.call_tool("test", {})
if result.ack:
    print(result.result)  # 実際の結果にアクセス
else:
    print(f"失敗: {result.rmcp_meta.error_message}")
```

### 問題: サーバー互換性

```python
# ❌ 問題
# サーバーがMCP-Tx実験的機能をサポートしていない

# ✅ 解決 - 自動フォールバック
rmcp_session = MCP-TxSession(mcp_session)
await rmcp_session.initialize()

if rmcp_session.rmcp_enabled:
    print("✅ MCP-Tx機能アクティブ")
else:
    print("⚠️ 標準MCPにフォールバック")
    # MCP-Txは動作するが、サーバーサイド機能なし
```

### 問題: パフォーマンス懸念

```python
# ❌ 問題
# MCP-Txが単純操作にオーバーヘッドを追加

# ✅ 解決 - 選択的使用
class HybridClient:
    def __init__(self, mcp_session):
        self.mcp_session = mcp_session
        self.rmcp_session = MCP-TxSession(mcp_session)
    
    async def simple_call(self, tool: str, args: dict):
        # 単純、非重要操作にはMCPを使用
        return await self.mcp_session.call_tool(tool, args)
    
    async def critical_call(self, tool: str, args: dict):
        # 信頼性が必要な重要操作にはMCP-Txを使用
        result = await self.rmcp_session.call_tool(tool, args)
        return result.result if result.ack else None
```

## 移行のベストプラクティス

### 1. 小さく始める
- 非重要操作から開始
- 重要システムに段階的に拡張
- 簡単なロールバックのためフィーチャーフラグを使用

### 2. 既存APIを保持
```python
# ✅ 良い: 既存関数シグネチャを維持
async def read_file(path: str) -> str:
    result = await rmcp_session.call_tool("file_reader", {"path": path})
    
    if not result.ack:
        raise RuntimeError(f"ファイル読み込み失敗: {result.rmcp_meta.error_message}")
    
    return result.result["content"]

# ❌ 悪い: 呼び出し元にMCP-Tx詳細を強制
async def read_file(path: str) -> MCP-TxResult:
    return await rmcp_session.call_tool("file_reader", {"path": path})
```

### 3. MCP-Tx機能を段階的に活用
1. **フェーズ1**: 基本ラッパー（自動リトライ、エラーハンドリング）
2. **フェーズ2**: 書き込み操作に冪等性を追加
3. **フェーズ3**: 異なる操作タイプ用カスタムリトライポリシー
4. **フェーズ4**: 高度機能（トランザクション、監視）

### 4. 監視と測定
- 信頼性メトリクス（成功率、リトライ回数）を追跡
- パフォーマンス影響（レイテンシ、スループット）を監視
- 移行前後のエラー率を比較
- MCP-Tx固有問題のアラートを設定

---

**次へ**: [FAQ](faq_jp.md) | **前へ**: [例](examples/basic_jp.md) ←