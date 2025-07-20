# トラブルシューティングガイド

MCP-Txを使用する際の一般的な問題と解決策。

## インストール問題

### "No module named 'rmcp'"

**問題**: MCP-Txを使用しようとした際のインポートエラー
```python
ModuleNotFoundError: No module named 'rmcp'
```

**解決策**:
```bash
# uv（推奨）でインストール
uv add mcp_tx

# またはpipでインストール
pip install mcp_tx

# インストール確認
python -c "import rmcp; print(rmcp.__version__)"
```

### 依存関係の競合

**問題**: インストール中のパッケージバージョン競合

**解決策**:
```bash
# 競合をチェック
uv tree

# 依存関係を更新
uv sync --upgrade

# 新しい仮想環境を使用
uv venv --clear
source .venv/bin/activate  # Linux/Mac
# または .venv\Scripts\activate  # Windows
uv add mcp_tx
```

## セッション初期化問題

### "MCP-Tx session not initialized"

**問題**: セッションを初期化せずに`call_tool()`を呼び出し
```python
rmcp_session = MCP-TxSession(mcp_session)
result = await rmcp_session.call_tool("test", {})  # エラー！
```

**解決策**: 常に最初に`initialize()`を呼び出し
```python
rmcp_session = MCP-TxSession(mcp_session)
await rmcp_session.initialize()  # 必須！
result = await rmcp_session.call_tool("test", {})
```

### サーバー機能ネゴシエーション失敗

**問題**: サーバーがMCP-Tx機能に応答しない

**症状**:
- `rmcp_session.rmcp_enabled`が`False`
- すべての操作が標準MCPにフォールバック

**解決策**:
```python
# 初期化後にサーバー機能をチェック
await rmcp_session.initialize()
if not rmcp_session.rmcp_enabled:
    print("⚠️ サーバーがMCP-Txをサポートしていません - フォールバックモード使用")
    # これは多くのサーバーで正常で期待される動作

# ネゴシエーションを確認するためデバッグログを強制
import logging
logging.getLogger("rmcp").setLevel(logging.DEBUG)
```

### 非同期コンテキストマネージャー問題

**問題**: セッションが適切にクローズされず、リソースリーク

**悪いパターン**:
```python
rmcp = MCP-TxSession(mcp_session)
await rmcp.initialize()
# ... rmcpを使用
# セッションがクローズされない - リソースリーク！
```

**良いパターン**:
```python
# ✅ 最良: 非同期コンテキストマネージャーを使用
async with MCP-TxSession(mcp_session) as rmcp:
    await rmcp.initialize()
    # ... rmcpを使用
    # 自動的にクローズ

# ✅ 許容: 手動クリーンアップ
rmcp = MCP-TxSession(mcp_session)
try:
    await rmcp.initialize()
    # ... rmcpを使用
finally:
    await rmcp.close()
```

## 結果処理問題

### "MCP-TxResult object has no attribute 'content'"

**問題**: MCP結果に直接アクセスしようとしている
```python
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})
content = result.content  # AttributeError!
```

**解決策**: `.result`属性を通じて結果にアクセス
```python
result = await rmcp_session.call_tool("file_reader", {"path": "/data.txt"})

if result.ack:
    content = result.result.get("content", "")  # ✅ 正しい
    print(f"ファイル内容: {content}")
else:
    print(f"失敗: {result.rmcp_meta.error_message}")
```

### ACK vs Processed状態の混乱

**問題**: `result.ack` vs `result.processed`の誤解

**説明**:
```python
result = await rmcp_session.call_tool("test_tool", {})

# result.ack = True の意味:
#   - リクエストがサーバーに配信された
#   - サーバーが処理を試行した
#   - サーバーが承認を返送した

# result.processed = True の意味:
#   - ツールが実際に実行された
#   - ツールが完了した（成功またはエラー）
#   - 結果がresult.resultで利用可能

# 異なるシナリオで両方をチェック
if result.ack and result.processed:
    print("✅ ツール実行成功")
    print(f"結果: {result.result}")
elif result.ack and not result.processed:
    print("⚠️ サーバーはリクエストを受信したがツールを実行できなかった")
    print(f"理由: {result.rmcp_meta.error_message}")
else:
    print("❌ リクエストがサーバーに到達または承認を得られなかった")
    print(f"エラー: {result.rmcp_meta.error_message}")
```

## 設定問題

### 大きな操作でのタイムアウトエラー

**問題**: 大きなデータでの操作がタイムアウト
```python
# デフォルト10秒後にタイムアウト
result = await rmcp_session.call_tool("process_large_file", {"path": "/huge.csv"})
# MCP-TxTimeoutError!
```

**解決策**:
```python
# 解決策1: 呼び出しごとのタイムアウトオーバーライド
result = await rmcp_session.call_tool(
    "process_large_file",
    {"path": "/huge.csv"},
    timeout_ms=300000  # 5分
)

# 解決策2: セッションデフォルトを設定
config = MCP-TxConfig(default_timeout_ms=60000)  # 1分デフォルト
rmcp_session = MCP-TxSession(mcp_session, config)

# 解決策3: 環境固有設定
def get_timeout_for_environment():
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return 30000  # 30秒
    elif env == "staging":
        return 15000  # 15秒
    else:
        return 5000   # 5秒（高速開発サイクル）

config = MCP-TxConfig(default_timeout_ms=get_timeout_for_environment())
```

### メモリ使用量の時間的増加

**問題**: 長時間実行セッションでメモリ使用量が増加

**原因**:
- 大きな重複排除キャッシュ
- 多くの並行リクエスト
- リクエスト追跡がクリーンアップされない

**解決策**:
```python
# キャッシュウィンドウを減らす
config = MCP-TxConfig(
    deduplication_window_ms=300000,  # デフォルト10分ではなく5分
    max_concurrent_requests=5,       # 並行リクエストを制限
)

# メモリ使用量を監視
import psutil
import os

def check_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"メモリ使用量: {memory_mb:.1f} MB")

# 定期的にチェック
check_memory()
result = await rmcp_session.call_tool("test", {})
check_memory()
```

### リトライポリシーが期待通りに動作しない

**問題**: リトライが発生しないか、過度に積極的

**一般的な問題**:
```python
# ❌ 問題: リトライ可能エラーがないリトライポリシー
bad_policy = RetryPolicy(
    max_attempts=5,
    retryable_errors=[]  # 空のリスト - 何もリトライしない！
)

# ✅ 解決策: 適切なエラータイプを含める
good_policy = RetryPolicy(
    max_attempts=5,
    retryable_errors=["CONNECTION_ERROR", "TIMEOUT", "NETWORK_ERROR"]
)

# ❌ 問題: 過度に積極的なリトライ
aggressive_policy = RetryPolicy(
    max_attempts=10,        # 試行回数が多すぎ
    base_delay_ms=100,      # 遅延が短すぎ
    backoff_multiplier=1.0  # バックオフなし！
)

# ✅ 解決策: 合理的なリトライポリシー
reasonable_policy = RetryPolicy(
    max_attempts=3,         # 合理的な試行回数
    base_delay_ms=1000,     # 1秒ベース遅延
    backoff_multiplier=2.0, # 指数バックオフ
    jitter=True            # サンダリングハード防止
)
```

## エラーハンドリング問題

### 汎用例外処理で問題が隠される

**問題**: すべての例外をキャッチすると重要なエラーコンテキストを失う
```python
# ❌ 悪い: 汎用例外処理
try:
    result = await rmcp_session.call_tool("api_call", {})
except Exception as e:
    print(f"何かがうまくいかなかった: {e}")
    return None  # すべてのエラーコンテキストを失った！
```

**解決策**: 特定のMCP-Tx例外を処理
```python
# ✅ 良い: 特定例外処理
from rmcp.types import MCP-TxTimeoutError, MCP-TxNetworkError

try:
    result = await rmcp_session.call_tool("api_call", {})
    
except MCP-TxTimeoutError as e:
    print(f"操作が{e.details['timeout_ms']}ms後にタイムアウト")
    # より長いタイムアウトでリトライするか、異なるアプローチ
    
except MCP-TxNetworkError as e:
    print(f"ネットワークエラー: {e.message}")
    # ネットワーク接続をチェックするか、後でリトライ
    
except ValueError as e:
    print(f"無効な入力パラメータ: {e}")
    # 入力を修正して再試行
    
except Exception as e:
    print(f"予期しないエラー: {e}")
    # デバッグ用にログ、それでも適切に処理
```

### エラーメッセージの説明不足

**問題**: エラーメッセージがデバッグに十分なコンテキストを提供しない

**解決策**:
```python
# より詳細なデバッグログを有効化
import logging
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# より多くのコンテキスト付きカスタムエラーハンドラーを作成
async def call_tool_with_context(tool_name: str, arguments: dict):
    try:
        return await rmcp_session.call_tool(tool_name, arguments)
    except Exception as e:
        print(f"ツール呼び出し失敗:")
        print(f"  ツール: {tool_name}")
        print(f"  引数: {arguments}")
        print(f"  エラー: {e}")
        print(f"  MCP-Tx有効: {rmcp_session.rmcp_enabled}")
        print(f"  アクティブリクエスト: {len(rmcp_session.active_requests)}")
        raise
```

## パフォーマンス問題

### 遅いツール呼び出し

**問題**: MCP-Tx操作が期待より遅い

**デバッグステップ**:
```python
import time

async def benchmark_call(tool_name: str, arguments: dict):
    start_time = time.time()
    
    result = await rmcp_session.call_tool(tool_name, arguments)
    
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    
    print(f"ツール: {tool_name}")
    print(f"期間: {duration_ms:.1f}ms") 
    print(f"試行回数: {result.attempts}")
    print(f"MCP-Tx有効: {rmcp_session.rmcp_enabled}")
    
    return result

# 直接MCP呼び出しと比較
start_time = time.time()
direct_result = await mcp_session.call_tool(tool_name, arguments)
direct_duration = (time.time() - start_time) * 1000

print(f"直接MCP: {direct_duration:.1f}ms")
print(f"MCP-Txオーバーヘッド: {duration_ms - direct_duration:.1f}ms")
```

**一般的な原因と解決策**:
```python
# リソース競合を引き起こす高い並行性制限
config = MCP-TxConfig(max_concurrent_requests=5)  # デフォルト10から削減

# 不必要なリトライ試行
quick_policy = RetryPolicy(max_attempts=1)  # 単純操作にはリトライなし
result = await rmcp_session.call_tool("fast_op", {}, retry_policy=quick_policy)

# メモリ圧迫を引き起こす大きな重複排除キャッシュ
config = MCP-TxConfig(deduplication_window_ms=60000)  # 10分ではなく1分
```

### 高いリトライ率

**問題**: 多すぎる操作がリトライを必要とする

**調査**:
```python
# リトライ統計を追跡
retry_stats = {"total": 0, "retried": 0, "max_attempts": 0}

async def track_retries(tool_name: str, arguments: dict):
    result = await rmcp_session.call_tool(tool_name, arguments)
    
    retry_stats["total"] += 1
    if result.attempts > 1:
        retry_stats["retried"] += 1
        retry_stats["max_attempts"] = max(retry_stats["max_attempts"], result.attempts)
    
    return result

# 操作実行後
retry_rate = retry_stats["retried"] / retry_stats["total"] * 100
print(f"リトライ率: {retry_rate:.1f}%")
print(f"最大試行回数: {retry_stats['max_attempts']}")

# リトライ率 > 20%の場合、調査:
# 1. ネットワーク安定性
# 2. サーバー信頼性  
# 3. タイムアウト設定
# 4. リソース競合
```

## デバッグツール

### デバッグログ有効化

```python
import logging

# MCP-Tx内部用ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 特定ロガー
rmcp_logger = logging.getLogger("rmcp")
rmcp_logger.setLevel(logging.DEBUG)

# これでMCP-Txは以下をログ出力:
# - リクエストID生成
# - リトライ試行と遅延  
# - キャッシュヒット/ミス
# - サーバー機能ネゴシエーション
# - エラー詳細とコンテキスト
```

### セッション内省

```python
async def debug_session_state(rmcp_session: MCP-TxSession):
    print("=== MCP-Txセッションデバッグ情報 ===")
    print(f"MCP-Tx有効: {rmcp_session.rmcp_enabled}")
    print(f"アクティブリクエスト: {len(rmcp_session.active_requests)}")
    
    for req_id, tracker in rmcp_session.active_requests.items():
        print(f"  {req_id}: {tracker.status} ({tracker.attempts} 試行)")
    
    # メモリ使用量
    import sys
    print(f"セッションオブジェクトサイズ: {sys.getsizeof(rmcp_session)} バイト")
    
    # 設定
    config = rmcp_session.config
    print(f"デフォルトタイムアウト: {config.default_timeout_ms}ms")
    print(f"最大並行数: {config.max_concurrent_requests}")
    print(f"重複排除ウィンドウ: {config.deduplication_window_ms}ms")

# デバッグ中に定期的に呼び出し
await debug_session_state(rmcp_session)
```

### ネットワーク診断

```python
import aiohttp
import asyncio

async def test_network_connectivity():
    """基本ネットワーク接続をテスト"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://httpbin.org/get", timeout=5) as response:
                if response.status == 200:
                    print("✅ ネットワーク接続OK")
                else:
                    print(f"⚠️ ネットワーク問題: ステータス {response.status}")
    except asyncio.TimeoutError:
        print("❌ ネットワークタイムアウト")
    except Exception as e:
        print(f"❌ ネットワークエラー: {e}")

async def test_mcp_connectivity(mcp_session):
    """直接MCP接続をテスト"""
    try:
        # 単純なMCP操作を試行
        result = await mcp_session.call_tool("echo", {"message": "test"})
        print("✅ MCP接続OK")
    except Exception as e:
        print(f"❌ MCP接続問題: {e}")

# 診断実行
await test_network_connectivity()
await test_mcp_connectivity(mcp_session)
```

## ヘルプの取得

### バグレポートに含めるべき情報

問題を報告する際は以下を含めてください:

1. **環境情報**:
```python
import sys
import rmcp
print(f"Pythonバージョン: {sys.version}")
print(f"MCP-Txバージョン: {rmcp.__version__}")
print(f"プラットフォーム: {sys.platform}")
```

2. **設定**:
```python
print(f"MCP-Tx設定: {rmcp_session.config}")
print(f"MCP-Tx有効: {rmcp_session.rmcp_enabled}")
```

3. **エラー詳細**:
```python
# 完全な例外トレースバック
# 特定のエラーメッセージ
# 再現手順
# 期待される動作と実際の動作
```

4. **デバッグログ**:
```python
# デバッグログを有効化して関連ログ出力を含める
logging.getLogger("rmcp").setLevel(logging.DEBUG)
```

### コミュニティリソース

- **GitHub Issues**: [reliable-MCP-draft/issues](https://github.com/Daku-on/reliable-MCP-draft/issues)
- **ドキュメント**: このdocsディレクトリ
- **例**: `docs/examples/` ディレクトリ

---

**前へ**: [FAQ](faq_jp.md) | **次へ**: [パフォーマンスガイド](performance_jp.md)