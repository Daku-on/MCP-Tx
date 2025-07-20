# MCP-Tx設定ガイド

このガイドでは、基本設定から高度なチューニングまで、MCP-Txで利用可能なすべての設定オプションについて説明します。

## クイックスタート設定

### 基本セットアップ

```python
from rmcp import MCP-TxConfig, MCP-TxSession

# デフォルト設定（ほとんどのユースケースに推奨）
config = MCP-TxConfig()
session = MCP-TxSession(mcp_session, config)
```

### 一般的なカスタマイズ

```python
from rmcp import MCP-TxConfig, RetryPolicy

# 本番対応の設定
config = MCP-TxConfig(
    # タイムアウト
    default_timeout_ms=30000,        # 30秒
    
    # 同時実行
    max_concurrent_requests=10,      # 並列操作を制限
    
    # 重複排除
    deduplication_window_ms=300000,  # 5分間
    
    # リトライ動作
    retry_policy=RetryPolicy(
        max_attempts=3,
        base_delay_ms=1000,
        backoff_multiplier=2.0
    ),
    
    # ログ
    enable_request_logging=True,
    log_level="INFO"
)
```

## 設定オプション

### MCP-TxConfigパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|---------|-------------|
| `default_timeout_ms` | int | 60000 | すべての操作のデフォルトタイムアウト（ミリ秒） |
| `max_concurrent_requests` | int | 100 | 最大並列リクエスト数 |
| `deduplication_window_ms` | int | 300000 | リクエストIDの記憶時間（5分間） |
| `retry_policy` | RetryPolicy | 下記参照 | デフォルトリトライ動作 |
| `enable_request_logging` | bool | False | すべてのリクエスト/レスポンスをログ |
| `log_level` | str | "INFO" | ログの詳細度 |
| `max_message_size` | int | 10MB | 最大メッセージサイズ |
| `enable_compression` | bool | False | 大きなメッセージを圧縮 |

### RetryPolicyパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|---------|-------------|
| `max_attempts` | int | 3 | 最大リトライ試行回数 |
| `base_delay_ms` | int | 1000 | 初回リトライ遅延（ミリ秒） |
| `max_delay_ms` | int | 60000 | 最大リトライ遅延 |
| `backoff_multiplier` | float | 2.0 | 指数バックオフ係数 |
| `jitter` | bool | True | サンダリングハード防止のためのランダム性追加 |
| `retry_on_timeout` | bool | True | タイムアウトエラーをリトライ |

## FastMCP-Tx設定

### アプリレベル設定

```python
from rmcp import FastMCP-Tx, MCP-TxConfig

# FastMCP-Txアプリを設定
config = MCP-TxConfig(
    default_timeout_ms=20000,
    enable_request_logging=True
)

app = FastMCP-Tx(
    mcp_session,
    config=config,
    name="Production App",
    max_tools=500  # ツールレジストリサイズを制限
)
```

### ツールレベル設定

```python
@app.tool(
    # このツール用のカスタムリトライ
    retry_policy=RetryPolicy(
        max_attempts=5,
        base_delay_ms=2000
    ),
    
    # ツール固有のタイムアウト
    timeout_ms=45000,
    
    # カスタム冪等性
    idempotency_key_generator=lambda args: f"tool-{args['id']}"
)
async def critical_tool(id: str, data: dict) -> dict:
    """カスタム設定でのツール"""
    return {"processed": True}
```

## 環境ベース設定

### 環境変数の使用

```python
import os
from rmcp import MCP-TxConfig

# 環境から読み取り
config = MCP-TxConfig(
    default_timeout_ms=int(os.getenv("MCP-Tx_TIMEOUT", "30000")),
    max_concurrent_requests=int(os.getenv("MCP-Tx_MAX_CONCURRENT", "10")),
    enable_request_logging=os.getenv("MCP-Tx_LOGGING", "false").lower() == "true"
)
```

### 設定ファイル

```python
import json
from pathlib import Path
from rmcp import MCP-TxConfig, RetryPolicy

# JSONファイルから読み込み
config_path = Path("rmcp_config.json")
if config_path.exists():
    with open(config_path) as f:
        config_data = json.load(f)
    
    config = MCP-TxConfig(
        default_timeout_ms=config_data.get("timeout_ms", 30000),
        retry_policy=RetryPolicy(**config_data.get("retry", {})),
        **config_data.get("options", {})
    )
else:
    config = MCP-TxConfig()  # デフォルト
```

例 `rmcp_config.json`:
```json
{
  "timeout_ms": 30000,
  "retry": {
    "max_attempts": 5,
    "base_delay_ms": 1000,
    "backoff_multiplier": 2.0
  },
  "options": {
    "max_concurrent_requests": 20,
    "enable_request_logging": true
  }
}
```

## 高度な設定

### カスタムリトライ戦略

```python
from rmcp import RetryPolicy

# 異なるシナリオ用の異なる戦略
AGGRESSIVE_RETRY = RetryPolicy(
    max_attempts=10,
    base_delay_ms=100,
    max_delay_ms=5000,
    backoff_multiplier=1.5
)

CONSERVATIVE_RETRY = RetryPolicy(
    max_attempts=3,
    base_delay_ms=5000,
    max_delay_ms=60000,
    backoff_multiplier=3.0
)

# 操作タイプに基づいて適用
@app.tool(retry_policy=AGGRESSIVE_RETRY)
async def network_operation(): ...

@app.tool(retry_policy=CONSERVATIVE_RETRY)
async def expensive_operation(): ...
```

### 動的設定

```python
class DynamicMCP-TxConfig:
    """実行時に更新可能な設定"""
    
    def __init__(self):
        self._config = MCP-TxConfig()
        self._overrides = {}
    
    def update_timeout(self, operation: str, timeout_ms: int):
        """特定の操作のタイムアウトを更新"""
        self._overrides[operation] = {"timeout_ms": timeout_ms}
    
    def get_config(self, operation: str) -> dict:
        """操作の設定を取得"""
        base = self._config.__dict__.copy()
        base.update(self._overrides.get(operation, {}))
        return base

# 使用例
dynamic_config = DynamicMCP-TxConfig()
dynamic_config.update_timeout("slow_operation", 120000)  # 2分
```

### パフォーマンスチューニング

```python
# 高スループット設定
high_throughput_config = MCP-TxConfig(
    max_concurrent_requests=50,
    default_timeout_ms=10000,  # 高速失敗
    retry_policy=RetryPolicy(
        max_attempts=2,  # 最小リトライ
        base_delay_ms=100
    ),
    enable_compression=True,  # 帯域幅削減
    enable_request_logging=False  # オーバーヘッド削減
)

# 高信頼性設定
high_reliability_config = MCP-TxConfig(
    max_concurrent_requests=5,  # 負荷制限
    default_timeout_ms=60000,  # 忍耐強いタイムアウト
    retry_policy=RetryPolicy(
        max_attempts=10,  # 積極的リトライ
        base_delay_ms=5000,
        jitter=True
    ),
    deduplication_window_ms=3600000,  # 1時間
    enable_request_logging=True  # 完全な監査証跡
)
```

## モニタリング設定

### メトリクス収集

```python
from rmcp import MCP-TxConfig
import logging

# メトリクス付き設定
config = MCP-TxConfig(
    enable_request_logging=True,
    log_level="DEBUG"
)

# カスタムメトリクスハンドラ
class MetricsHandler(logging.Handler):
    def emit(self, record):
        if hasattr(record, 'rmcp_metrics'):
            # モニタリングシステムに送信
            metrics = record.rmcp_metrics
            send_to_prometheus(metrics)

# MCP-Txロガーに付加
logger = logging.getLogger('rmcp')
logger.addHandler(MetricsHandler())
```

### ヘルスチェック

```python
class HealthCheckConfig:
    """内蔵ヘルスモニタリング付き設定"""
    
    def __init__(self, base_config: MCP-TxConfig):
        self.base_config = base_config
        self.health_threshold = 0.95  # 95%成功率
        self.check_interval_ms = 30000  # 30秒
    
    async def health_check(self, session: MCP-TxSession) -> bool:
        """セッションが健全かチェック"""
        try:
            result = await session.call_tool(
                "health_check",
                {},
                timeout_ms=5000
            )
            return result.rmcp_meta.ack
        except:
            return False
```

## 設定のベストプラクティス

### 1. デフォルトから開始

```python
# 良い例: 特定の要件がない限りデフォルトを使用
config = MCP-TxConfig()

# 必要なもののみカスタマイズ
config.default_timeout_ms = 45000  # 特定の要件
```

### 2. 環境固有の設定

```python
# 開発環境
dev_config = MCP-TxConfig(
    enable_request_logging=True,
    log_level="DEBUG",
    retry_policy=RetryPolicy(max_attempts=1)  # 開発では高速失敗
)

# 本番環境
prod_config = MCP-TxConfig(
    enable_request_logging=True,
    log_level="INFO",
    retry_policy=RetryPolicy(max_attempts=5),
    enable_compression=True
)
```

### 3. 選択の文書化

```python
# 高頻度取引システムの設定
config = MCP-TxConfig(
    # マーケットデータは時間に敏感なため低タイムアウト
    default_timeout_ms=500,
    
    # リトライなし - 古いデータは無データより悪い
    retry_policy=RetryPolicy(max_attempts=1),
    
    # 並列マーケットクエリのため高同時実行
    max_concurrent_requests=100
)
```

## 設定のトラブルシューティング

### デバッグモード

```python
# すべてのデバッグ機能を有効化
debug_config = MCP-TxConfig(
    enable_request_logging=True,
    log_level="DEBUG",
    # デバッグ用にリトライを遅く
    retry_policy=RetryPolicy(
        base_delay_ms=5000,
        jitter=False  # 予測可能なタイミング
    )
)
```

### よくある問題

1. **タイムアウトが積極的すぎる**
   ```python
   # 遅い操作のタイムアウトを増加
   config.default_timeout_ms = 120000  # 2分
   ```

2. **リトライが多すぎる**
   ```python
   # ユーザー向け操作のリトライ試行を削減
   config.retry_policy.max_attempts = 2
   ```

3. **重複排除でのメモリ問題**
   ```python
   # 重複排除ウィンドウを削減
   config.deduplication_window_ms = 60000  # 1分
   ```

## 関連ドキュメント

- [はじめに](getting-started_jp.md) - クイックスタートガイド
- [API リファレンス](api/rmcp-session_jp.md) - 詳細なAPI仕様
- [パフォーマンスガイド](performance_jp.md) - 最適化のヒント

---

**前へ**: [信頼性機能](reliability-features_jp.md) | **次へ**: [パフォーマンスガイド](performance_jp.md)