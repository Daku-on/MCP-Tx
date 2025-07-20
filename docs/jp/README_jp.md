# RMCP ドキュメント

Reliable Model Context Protocol (RMCP) の完全なドキュメント

## RMCPとは？

**RMCP (Reliable Model Context Protocol)** は、既存のMCPセッションに信頼性レイヤーを提供するPythonライブラリです。配信保証、自動リトライ、リクエスト重複排除、トランザクション追跡を追加しながら、既存のMCPサーバーとの100%後方互換性を維持します。

## 主な機能

- ✅ **配信保証** - ACK/NACKメカニズム
- ✅ **自動リトライ** - 指数バックオフとジッター
- ✅ **冪等性** - 重複実行の防止
- ✅ **リッチなエラーハンドリング** - 詳細なコンテキスト付き
- ✅ **リクエスト追跡** - トランザクションライフサイクル管理
- ✅ **100%後方互換性** - 既存のMCPサーバーで動作

## クイックスタート

```python
from rmcp import RMCPSession
from mcp.client.session import ClientSession

# 既存のMCPセッションをラップ
mcp_session = ClientSession(...)
rmcp_session = RMCPSession(mcp_session)

await rmcp_session.initialize()

# 信頼性保証付きツール呼び出し
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

if result.ack:
    print(f"成功: {result.result}")
    print(f"試行回数: {result.attempts}")
else:
    print(f"失敗: {result.rmcp_meta.error_message}")
```

## ドキュメント構造

### 📖 コアドキュメント

| ドキュメント | 説明 | 対象 |
|-------------|------|------|
| [**はじめる**](getting-started_jp.md) | 5分でRMCPを始める | 新規ユーザー |
| [**アーキテクチャ**](architecture_jp.md) | 技術的な深掘り | 開発者 |
| [**信頼性機能**](reliability-features_jp.md) | ACK/NACK、リトライ、冪等性 | 開発者 |
| [**設定ガイド**](configuration_jp.md) | 詳細設定オプション | 開発者・運用 |
| [**パフォーマンス**](performance_jp.md) | 本番最適化ガイド | 運用チーム |
| [**移行ガイド**](migration_jp.md) | MCPからRMCPへの移行 | 既存ユーザー |
| [**互換性**](compatibility_jp.md) | バージョン・プラットフォーム対応 | すべて |
| [**FAQ**](faq_jp.md) | よくある質問と回答 | すべて |
| [**トラブルシューティング**](troubleshooting_jp.md) | 問題解決ガイド | 運用チーム |

### 📋 APIリファレンス

| API | 説明 |
|-----|------|
| [**RMCPSession**](api/rmcp-session_jp.md) | メインインターフェース |

### 💡 実用的な例

| 例 | 説明 |
|----|------|
| [**基本的な使用方法**](examples/basic_jp.md) | 一般的な使用パターン |
| [**高度な例**](examples/advanced_jp.md) | 複雑なワークフローと統合 |
| [**フレームワーク統合**](examples/integration_jp.md) | Django、Flask、Celery統合 |

## 使用シナリオ

### 🔄 信頼性が重要な操作
```python
# ファイル処理 - 冪等性保証
result = await rmcp_session.call_tool(
    "file_processor",
    {"path": "/critical_data.csv", "operation": "validate"},
    idempotency_key="validate-critical-2024-01-15"
)
```

### 🌐 外部API呼び出し
```python
# カスタムリトライポリシー付きAPI呼び出し
api_retry = RetryPolicy(max_attempts=5, base_delay_ms=1000)
result = await rmcp_session.call_tool(
    "http_client", 
    {"url": "https://api.example.com/data"},
    retry_policy=api_retry,
    timeout_ms=30000
)
```

### ⚡ 高負荷システム
```python
# 並行制御付き設定
config = RMCPConfig(
    max_concurrent_requests=20,
    default_timeout_ms=15000
)
rmcp_session = RMCPSession(mcp_session, config)
```

## パフォーマンス概要

| メトリック | 標準MCP | RMCP | オーバーヘッド |
|------------|---------|------|-------------|
| **レイテンシ** | ベースライン | +2-5% | < 1ms |
| **メモリ** | ベースライン | +10-100KB | リクエスト追跡 |
| **ネットワーク** | ベースライン | +200-500バイト | RMCPメタデータ |
| **スループット** | ベースライン | 同等 | 最小限の影響 |

## インストール

```bash
# uv（推奨）
uv add rmcp

# pip
pip install rmcp
```

## 要件

- **Python**: 3.9+
- **依存関係**: `anyio`, `mcp` (既存のMCPライブラリ)
- **互換性**: すべてのMCPサーバー（RMCP対応・非対応問わず）

## サポート

### 🆘 ヘルプが必要ですか？

1. **[トラブルシューティングガイド](troubleshooting.jp.md)** をチェック
2. **[FAQ](faq.jp.md)** で一般的な質問を確認
3. **[GitHub Issues](https://github.com/takako/reliable-MCP-draft/issues)** で問題を報告

### 📚 詳細情報

- **初心者**: [はじめる](getting-started.jp.md) から開始
- **開発者**: [アーキテクチャ](architecture.jp.md) で技術詳細を確認
- **既存ユーザー**: [移行ガイド](migration.jp.md) でアップグレード方法を確認

---

**🚀 今すぐ始める**: [はじめる](getting-started.jp.md) →