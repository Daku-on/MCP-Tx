# はじめる

5分でRMCP (Reliable Model Context Protocol) の使用を開始しましょう。

## インストール

```bash
# uv（推奨）
uv add rmcp

# pip
pip install rmcp

# インストール確認
python -c "import rmcp; print(f'RMCP {rmcp.__version__} installed')"
```

## 基本的な使用方法

### ステップ 1: 既存のMCPセッションをラップ

```python
import asyncio
import os
from rmcp import RMCPSession
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioClientTransport

async def main():
    # 既存のMCPセットアップ
    transport = StdioClientTransport(...)
    mcp_session = ClientSession(transport)
    
    # RMCPで信頼性機能を追加
    rmcp_session = RMCPSession(mcp_session)
    
    # 初期化（必須）
    await rmcp_session.initialize()
    
    # これで信頼性保証付きツール呼び出しが可能
    result = await rmcp_session.call_tool("echo", {"message": "Hello RMCP!"})
    
    if result.ack:
        print(f"成功: {result.result}")
    else:
        print(f"失敗: {result.rmcp_meta.error_message}")
    
    await rmcp_session.close()

asyncio.run(main())
```

### ステップ 2: 結果の理解

```python
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

# RMCPの保証をチェック
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
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 冪等性付きファイル書き込み
        write_result = await rmcp.call_tool(
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
        read_result = await rmcp.call_tool(
            "file_reader",
            {"path": "/output/report.txt"},
            timeout_ms=10000  # 10秒タイムアウト
        )
        
        if read_result.ack:
            print(f"📄 ファイル内容: {read_result.result['content']}")
```

### API呼び出しの信頼性

```python
from rmcp import RetryPolicy

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
    
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        result = await rmcp.call_tool(
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
            print(f"❌ API呼び出し失敗: {result.rmcp_meta.error_message}")
```

## 設定のカスタマイズ

### 環境固有の設定

```python
from rmcp import RMCPConfig, RetryPolicy
import os

def create_config():
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return RMCPConfig(
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
        return RMCPConfig(
            default_timeout_ms=5000,       # 5秒（開発用）
            retry_policy=RetryPolicy(
                max_attempts=2,
                base_delay_ms=500           # 0.5秒から開始
            ),
            max_concurrent_requests=5      # 開発環境では低めに
        )

# 設定を使用
config = create_config()
rmcp_session = RMCPSession(mcp_session, config)
```

### 操作別設定

```python
async def operation_specific_config():
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 高速操作 - 短いタイムアウト
        cache_result = await rmcp.call_tool(
            "cache_lookup",
            {"key": "user_123"},
            timeout_ms=2000  # 2秒
        )
        
        # 低速操作 - 長いタイムアウト
        ml_result = await rmcp.call_tool(
            "ml_inference",
            {"model": "large_language_model", "input": "データ"},
            timeout_ms=300000  # 5分
        )
        
        # 重要な操作 - 積極的リトライ
        critical_retry = RetryPolicy(max_attempts=10, base_delay_ms=500)
        backup_result = await rmcp.call_tool(
            "database_backup",
            {"target": "s3://backup-bucket"},
            retry_policy=critical_retry
        )
```

## エラーハンドリング

### 特定エラータイプの処理

```python
from rmcp.types import RMCPTimeoutError, RMCPNetworkError

async def robust_error_handling():
    try:
        result = await rmcp_session.call_tool("external_service", {})
        
        if result.ack:
            return result.result
        else:
            print(f"ツール実行失敗: {result.rmcp_meta.error_message}")
            
    except RMCPTimeoutError as e:
        print(f"タイムアウト: {e.details['timeout_ms']}ms後")
        # より長いタイムアウトで再試行
        return await rmcp_session.call_tool(
            "external_service", {}, timeout_ms=60000
        )
        
    except RMCPNetworkError as e:
        print(f"ネットワークエラー: {e.message}")
        # しばらく待ってから再試行
        await asyncio.sleep(5)
        return await rmcp_session.call_tool("external_service", {})
```

## 並行処理

### 複数操作の並列実行

```python
import asyncio

async def concurrent_operations():
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        # 複数のファイルを並列処理
        files = ["/data/file1.txt", "/data/file2.txt", "/data/file3.txt"]
        
        async def process_file(file_path):
            return await rmcp.call_tool(
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

# RMCP内部のデバッグログを有効化
logging.basicConfig(level=logging.DEBUG)
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# これでRMCPが以下をログ出力します:
# - リクエストID生成
# - リトライ試行と遅延
# - キャッシュヒット/ミス
# - サーバー機能ネゴシエーション
# - エラー詳細
```

### セッション状態監視

```python
async def monitor_session():
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        print(f"RMCP有効: {rmcp.rmcp_enabled}")
        print(f"アクティブリクエスト: {len(rmcp.active_requests)}")
        
        # 操作実行
        result = await rmcp.call_tool("test", {})
        
        print(f"試行回数: {result.attempts}")
        print(f"最終ステータス: {result.final_status}")
```

## よくある使用パターン

### パターン 1: ドロップイン置換

```python
# 前: 標準MCP
# result = await mcp_session.call_tool("tool", args)

# 後: RMCP（信頼性機能付き）
result = await rmcp_session.call_tool("tool", args)
if result.ack:
    actual_result = result.result  # 元のMCP結果
```

### パターン 2: 条件付きRMCP使用

```python
USE_RMCP = os.getenv("USE_RMCP", "false").lower() == "true"

if USE_RMCP:
    session = RMCPSession(mcp_session)
    await session.initialize()
else:
    session = mcp_session

# セッションを通常通り使用
result = await session.call_tool("tool", args)

# RMCP結果の場合は適切に処理
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
    
    async with RMCPSession(mcp_session) as rmcp:
        await rmcp.initialize()
        
        for item in items:
            try:
                result = await rmcp.call_tool(
                    "item_processor",
                    {"item": item},
                    idempotency_key=f"process-{item['id']}"
                )
                
                if result.ack:
                    results.append(result.result)
                else:
                    failed.append((item, result.rmcp_meta.error_message))
                    
            except Exception as e:
                failed.append((item, str(e)))
    
    print(f"✅ 成功: {len(results)}, ❌ 失敗: {len(failed)}")
    return results, failed
```

## 次のステップ

### 📚 さらに学ぶ

- **[アーキテクチャ](architecture.jp.md)** - RMCPの内部動作を理解
- **[移行ガイド](migration.jp.md)** - 既存のMCPコードをアップグレード
- **[FAQ](faq.jp.md)** - よくある質問と回答

### 🔧 詳細設定

- **[APIリファレンス](api/rmcp-session.jp.md)** - 完全なAPIドキュメント
- **[例集](examples/basic.jp.md)** - より多くの実用例

### 🆘 サポート

- **[トラブルシューティング](troubleshooting.jp.md)** - 問題解決ガイド
- **[GitHub Issues](https://github.com/takako/reliable-MCP-draft/issues)** - バグ報告・機能要求

---

**次へ**: [アーキテクチャ](architecture.jp.md) → | **前へ**: [ドキュメント](README.jp.md) ←