# RMCP互換性ガイド

このガイドでは、RMCPと標準MCP間の互換性、バージョン要件、移行の考慮事項について説明します。

## MCP互換性

### 完全な後方互換性

RMCPは標準MCPと100%後方互換性があります：

```python
# 任意のMCPサーバーで動作
async def use_with_any_mcp_server(mcp_session):
    # RMCPは既存のセッションをラップ
    rmcp_session = RMCPSession(mcp_session)
    
    # サーバーがRMCPをサポートしない場合、標準MCPのように動作
    result = await rmcp_session.call_tool("any_tool", {})
    
    # RMCP機能はオプション
    if hasattr(result, 'rmcp_meta'):
        print(f"RMCP有効: {result.rmcp_meta.ack}")
    else:
        print("標準MCPレスポンス")
```

### 機能検出

```python
async def detect_rmcp_support(session):
    """サーバーがRMCP機能をサポートするかチェック"""
    # 初期化中にRMCPが機能をネゴシエート
    info = await session.initialize()
    
    if 'experimental' in info.capabilities:
        rmcp = info.capabilities['experimental'].get('rmcp', {})
        return {
            'supported': bool(rmcp),
            'version': rmcp.get('version'),
            'features': rmcp.get('features', [])
        }
    
    return {'supported': False}
```

## バージョン要件

### Pythonバージョンサポート

| Pythonバージョン | RMCPサポート | 備考 |
|---------------|--------------|-------|
| 3.10+ | ✅ 完全サポート | 推奨 |
| 3.9 | ✅ 完全サポート | サポート |
| 3.8 | ⚠️ 制限あり | 型ヒントの調整が必要な場合 |
| 3.7以下 | ❌ サポートなし | モダンな非同期機能が必要 |

### MCP SDKバージョン

| MCP SDKバージョン | RMCP互換性 | 備考 |
|-----------------|-------------------|-------|
| 1.0.0+ | ✅ 完全サポート | 現在の標準 |
| 0.9.x | ✅ 互換 | 一部機能が制限される場合 |
| 0.8.x以下 | ⚠️ 部分的 | コア機能のみ |

### 依存関係バージョン

```toml
# pyproject.toml
[dependencies]
mcp-python-sdk = ">=1.0.0"
pydantic = ">=2.0.0"
anyio = ">=3.0.0"  # クロスプラットフォーム非同期用
```

## プロトコル互換性

### RMCPプロトコルバージョン

```python
# RMCPは複数のプロトコルバージョンをサポート
PROTOCOL_VERSIONS = {
    "0.1.0": {  # 現在のバージョン
        "features": ["ack", "retry", "idempotency"],
        "compatible_with": ["0.1.x"]
    },
    "0.2.0": {  # 将来のバージョン
        "features": ["ack", "retry", "idempotency", "transactions"],
        "compatible_with": ["0.1.x", "0.2.x"]
    }
}
```

### 機能ネゴシエーション

```typescript
// クライアントがサポートするバージョンを宣言
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "min_version": "0.1.0",
        "features": ["ack", "retry", "idempotency"]
      }
    }
  }
}

// サーバーが自身の機能で応答
{
  "capabilities": {
    "experimental": {
      "rmcp": {
        "version": "0.1.0",
        "features": ["ack", "retry"]  // サーバーはサブセットをサポートの場合
      }
    }
  }
}
```

## フレームワーク互換性

### 非同期フレームワークサポート

```python
# RMCPはクロスプラットフォーム非同期にanyioを使用
import anyio

# asyncioで動作（デフォルト）
import asyncio
app = FastRMCP(mcp_session)  # asyncioを使用

# trioでも動作
import trio
async def with_trio():
    async with anyio.create_task_group() as tg:
        app = FastRMCP(mcp_session)
        tg.start_soon(app.initialize)
```

### Webフレームワーク互換性

| フレームワーク | サポート | 統合方法 |
|-----------|-----------|-------------------|
| FastAPI | ✅ ネイティブ非同期 | 直接統合 |
| Django | ✅ 非同期ビュー経由 | async_to_syncラッパー |
| Flask | ✅ 拡張経由 | イベントループ管理 |
| Tornado | ✅ ネイティブ非同期 | 直接統合 |
| aiohttp | ✅ ネイティブ非同期 | 直接統合 |

## オペレーティングシステム互換性

### プラットフォームサポート

| プラットフォーム | サポートレベル | 備考 |
|----------|--------------|-------|
| Linux | ✅ 完全サポート | すべての機能が利用可能 |
| macOS | ✅ 完全サポート | すべての機能が利用可能 |
| Windows | ✅ 完全サポート | より良い非同期のためPython 3.8+が必要 |
| WSL | ✅ 完全サポート | WSL2でテスト済み |

### プラットフォーム固有の考慮事項

```python
import sys
from rmcp import RMCPConfig

def get_platform_config() -> RMCPConfig:
    """プラットフォーム最適化設定を取得"""
    if sys.platform == "win32":
        # Windows固有の最適化
        return RMCPConfig(
            max_concurrent_requests=50,  # Windowsは異なる制限
            use_uvloop=False  # Windowsでは利用不可
        )
    else:
        # Unix系システム
        return RMCPConfig(
            max_concurrent_requests=100,
            use_uvloop=True  # より良いパフォーマンス
        )
```

## 破壊的変更と移行

### RMCP 0.xから1.0への移行

```python
# 旧API（0.x）
result = await rmcp.call_tool("my_tool", {})
if result.acknowledged:  # 変更
    print(result.retry_count)  # 変更

# 新API（1.0）
result = await rmcp.call_tool("my_tool", {})
if result.rmcp_meta.ack:  # 新構造
    print(result.rmcp_meta.attempts)  # 名前変更
```

### 移行ヘルパー

```python
class CompatibilityWrapper:
    """後方互換性用ラッパー"""
    
    def __init__(self, rmcp_result):
        self._result = rmcp_result
    
    # 互換性のための古いプロパティ名
    @property
    def acknowledged(self):
        return self._result.rmcp_meta.ack
    
    @property
    def retry_count(self):
        return self._result.rmcp_meta.attempts - 1
    
    @property
    def result(self):
        return self._result.result

# 使用例
def make_compatible(result):
    """新しい結果を古い形式に変換"""
    return CompatibilityWrapper(result)
```

## 既知の互換性問題

### 1. Python 3.8の型ヒント

```python
# Python 3.9+の構文
def process(data: dict[str, Any]) -> list[str]:
    pass

# Python 3.8互換
from typing import Dict, List, Any

def process(data: Dict[str, Any]) -> List[str]:
    pass
```

### 2. WindowsでのAsyncIO

```python
# Python < 3.8のWindowsでは特別な処理が必要
import sys
import asyncio

if sys.platform == "win32" and sys.version_info < (3, 8):
    # Windows用のイベントループポリシーを設定
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### 3. 大きなメッセージの処理

```python
# 一部のMCPサーバーはメッセージサイズ制限がある
config = RMCPConfig(
    max_message_size=1024 * 1024,  # 1MB制限
    enable_compression=True  # 大きなメッセージを圧縮
)

# 送信前にメッセージサイズをチェック
async def safe_call_tool(app, name, arguments):
    arg_size = len(json.dumps(arguments))
    if arg_size > 1024 * 1024:
        raise ValueError(f"引数が大きすぎます: {arg_size}バイト")
    
    return await app.call_tool(name, arguments)
```

## 互換性テスト

### 互換性テストスイート

```python
import pytest
from rmcp import FastRMCP, RMCPSession

@pytest.mark.compatibility
class TestCompatibility:
    """様々な設定でのRMCP互換性をテスト"""
    
    async def test_standard_mcp_fallback(self, standard_mcp_session):
        """RMCPが非RMCPサーバーで動作することをテスト"""
        rmcp = RMCPSession(standard_mcp_session)
        
        # RMCP機能なしで動作するべき
        result = await rmcp.call_tool("echo", {"text": "hello"})
        assert result.result == {"text": "hello"}
        
        # RMCPメタデータはフォールバックを示すべき
        assert not hasattr(result, 'rmcp_meta') or not result.rmcp_meta.ack
    
    async def test_version_negotiation(self, mock_server):
        """プロトコルバージョンネゴシエーションをテスト"""
        # サーバーが古いバージョンをサポート
        mock_server.capabilities = {
            "experimental": {
                "rmcp": {"version": "0.0.9"}
            }
        }
        
        session = await connect_to_server(mock_server)
        assert session.rmcp_version == "0.0.9"  # サーバーバージョンを使用
    
    async def test_feature_degradation(self, limited_server):
        """優雅な機能劣化をテスト"""
        # サーバーはACKのみをサポート、リトライはなし
        app = FastRMCP(limited_server)
        
        @app.tool(retry_policy=RetryPolicy(max_attempts=3))
        async def test_tool():
            return "success"
        
        # 動作するがリトライなし
        result = await app.call_tool("test_tool", {})
        assert result.rmcp_meta.attempts == 1  # リトライは発生しない
```

### 互換性チェッカーツール

```python
# rmcp_check.py
async def check_compatibility(server_url: str):
    """サーバーとのRMCP互換性をチェック"""
    try:
        # サーバーに接続
        session = await connect_to_mcp_server(server_url)
        
        # 機能をチェック
        rmcp_support = await detect_rmcp_support(session)
        
        print(f"サーバー: {server_url}")
        print(f"RMCPサポート: {'あり' if rmcp_support['supported'] else 'なし'}")
        
        if rmcp_support['supported']:
            print(f"バージョン: {rmcp_support['version']}")
            print(f"機能: {', '.join(rmcp_support['features'])}")
        
        # 基本操作をテスト
        print("\n基本操作をテスト中...")
        
        # ツール呼び出しをテスト
        try:
            result = await session.call_tool("ping", {})
            print("✓ ツール呼び出し: サポート")
        except:
            print("✗ ツール呼び出し: サポートなし")
        
        # 利用可能な場合はRMCP機能をテスト
        if rmcp_support['supported']:
            rmcp_session = RMCPSession(session)
            
            # ACKをテスト
            result = await rmcp_session.call_tool("ping", {})
            if hasattr(result, 'rmcp_meta') and result.rmcp_meta.ack:
                print("✓ ACK/NACK: サポート")
            else:
                print("✗ ACK/NACK: サポートなし")
        
        await session.close()
        
    except Exception as e:
        print(f"互換性チェックエラー: {e}")

# 互換性チェックを実行
if __name__ == "__main__":
    import sys
    asyncio.run(check_compatibility(sys.argv[1]))
```

## 将来の互換性

### 計画されている機能

RMCPは前方互換性を持つよう設計されています：

```python
# 将来の機能はオプション
future_config = RMCPConfig(
    # 現在の機能
    enable_retry=True,
    enable_deduplication=True,
    
    # 将来の機能（現在のバージョンでは無視）
    enable_transactions=True,  # 将来
    enable_streaming=True,     # 将来
    enable_batching=True       # 将来
)
```

### バージョンポリシー

- **メジャーバージョン**（1.0、2.0）：破壊的変更がある場合
- **マイナーバージョン**（1.1、1.2）：新機能、後方互換
- **パッチバージョン**（1.0.1、1.0.2）：バグ修正のみ

## 関連ドキュメント

- [移行ガイド](migration_jp.md) - MCPからRMCPへのアップグレード
- [はじめに](getting-started_jp.md) - 初期セットアップ
- [FAQ](faq_jp.md) - 一般的な互換性質問

---

**前へ**: [移行ガイド](migration_jp.md) | **次へ**: [FAQ](faq_jp.md)