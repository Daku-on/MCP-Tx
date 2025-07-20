# MCP-Tx統合ガイド

このガイドでは、既存のMCPサーバーや人気のフレームワークとMCP-Txを統合する方法を示します。

## 既存MCPサーバーとの統合

### 基本MCPサーバー統合

```python
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioTransport
from rmcp import FastMCP-Tx, MCP-TxConfig
import asyncio

async def connect_to_mcp_server():
    """既存のMCPサーバーにMCP-Tx信頼性で接続"""
    
    # 標準MCPサーバーに接続
    transport = StdioTransport(
        command=["python", "-m", "mcp_server"],
        cwd="/path/to/server"
    )
    
    async with ClientSession(transport) as mcp_session:
        # MCP-Txでラップ
        config = MCP-TxConfig(
            default_timeout_ms=30000,
            enable_request_logging=True
        )
        
        app = FastMCP-Tx(mcp_session, config)
        
        # ツールラッパーを登録
        @app.tool()
        async def reliable_file_operation(path: str, operation: str) -> dict:
            """信頼性付きで既存ファイル操作をラップ"""
            return await mcp_session.call_tool(
                "file_operation",
                {"path": path, "operation": operation}
            )
        
        # MCP-Tx機能で使用
        async with app:
            result = await app.call_tool(
                "reliable_file_operation",
                {"path": "/data/file.txt", "operation": "read"}
            )
            print(f"操作は{result.rmcp_meta.attempts}回の試行で完了")
```

### 複数MCPサーバー統合

```python
class MultiServerMCP-Tx:
    """統一されたMCP-Txインターフェースで複数のMCPサーバーを統合"""
    
    def __init__(self):
        self.servers = {}
        self.apps = {}
    
    async def add_server(self, name: str, transport):
        """MCPサーバーをプールに追加"""
        session = ClientSession(transport)
        await session.__aenter__()
        
        app = FastMCP-Tx(session, name=f"MCP-Tx-{name}")
        await app.initialize()
        
        self.servers[name] = session
        self.apps[name] = app
        
        return app
    
    async def call_server_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict,
        **kwargs
    ):
        """特定のサーバーでツールを呼び出し"""
        if server_name not in self.apps:
            raise ValueError(f"不明なサーバー: {server_name}")
        
        return await self.apps[server_name].call_tool(
            tool_name,
            arguments,
            **kwargs
        )
    
    async def broadcast_tool(
        self,
        tool_name: str,
        arguments: dict,
        **kwargs
    ):
        """すべてのサーバーで同じツールを呼び出し"""
        tasks = [
            app.call_tool(tool_name, arguments, **kwargs)
            for app in self.apps.values()
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

# 使用例
multi_server = MultiServerMCP-Tx()

# 異なるMCPサーバーを追加
await multi_server.add_server(
    "filesystem",
    StdioTransport(["python", "-m", "mcp_filesystem_server"])
)
await multi_server.add_server(
    "database",
    StdioTransport(["python", "-m", "mcp_database_server"])
)

# 特定のサーバーを使用
file_result = await multi_server.call_server_tool(
    "filesystem",
    "read_file",
    {"path": "/data/config.json"}
)
```

## フレームワーク統合

### Django統合

```python
# rmcp_django/middleware.py
from django.conf import settings
from rmcp import FastMCP-Tx, MCP-TxConfig
import asyncio

class MCP-TxMiddleware:
    """MCP-Tx統合用Djangoミドルウェア"""
    
    _instance = None
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._setup_rmcp()
    
    def _setup_rmcp(self):
        """MCP-Tx接続を初期化"""
        if not MCP-TxMiddleware._instance:
            config = MCP-TxConfig(
                default_timeout_ms=settings.MCP-Tx_TIMEOUT,
                enable_request_logging=settings.DEBUG
            )
            
            # 同期コンテキストで初期化
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            mcp_session = self._create_mcp_session()
            MCP-TxMiddleware._instance = FastMCP-Tx(mcp_session, config)
            
            loop.run_until_complete(MCP-TxMiddleware._instance.initialize())
    
    def __call__(self, request):
        # リクエストにMCP-Txを付加
        request.rmcp = MCP-TxMiddleware._instance
        response = self.get_response(request)
        return response

# rmcp_django/views.py
from django.http import JsonResponse
from asgiref.sync import async_to_sync

def process_with_rmcp(request):
    """MCP-Txを使用するDjangoビュー"""
    tool_name = request.POST.get('tool')
    arguments = request.POST.get('arguments', {})
    
    # 同期コンテキストでMCP-Tx呼び出しを実行
    result = async_to_sync(request.rmcp.call_tool)(
        tool_name,
        arguments
    )
    
    return JsonResponse({
        'success': True,
        'result': result.result,
        'attempts': result.rmcp_meta.attempts
    })
```

### Flask統合

```python
# rmcp_flask/extension.py
from flask import Flask, g
from rmcp import FastMCP-Tx, MCP-TxConfig
import asyncio
from functools import wraps

class FlaskMCP-Tx:
    """MCP-Tx用Flask拡張"""
    
    def __init__(self, app=None):
        self.app = app
        self._rmcp = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Flask拡張を初期化"""
        app.config.setdefault('MCP-Tx_TIMEOUT', 30000)
        app.config.setdefault('MCP-Tx_MAX_RETRIES', 3)
        
        # 最初のリクエストでセットアップ
        app.before_first_request(self._setup_rmcp)
        app.teardown_appcontext(self._teardown_rmcp)
    
    def _setup_rmcp(self):
        """MCP-Tx接続を初期化"""
        config = MCP-TxConfig(
            default_timeout_ms=self.app.config['MCP-Tx_TIMEOUT'],
            retry_policy=RetryPolicy(
                max_attempts=self.app.config['MCP-Tx_MAX_RETRIES']
            )
        )
        
        # セッションとMCP-Txを作成
        mcp_session = self._create_mcp_session()
        self._rmcp = FastMCP-Tx(mcp_session, config)
        
        # イベントループで初期化
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._rmcp.initialize())
    
    @property
    def rmcp(self):
        """MCP-Txインスタンスを取得"""
        return self._rmcp

# Flaskアプリでの使用例
from flask import Flask, jsonify
from rmcp_flask import FlaskMCP-Tx

app = Flask(__name__)
rmcp_ext = FlaskMCP-Tx(app)

@app.route('/execute/<tool_name>', methods=['POST'])
def execute_tool(tool_name):
    """MCP-Txツールを実行"""
    from flask import request
    
    # 非同期操作を実行
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(
        rmcp_ext.rmcp.call_tool(tool_name, request.json)
    )
    
    return jsonify({
        'result': result.result,
        'metadata': {
            'attempts': result.rmcp_meta.attempts,
            'request_id': result.rmcp_meta.request_id
        }
    })
```

### Celery統合

```python
# rmcp_celery/tasks.py
from celery import Celery, Task
from rmcp import FastMCP-Tx, MCP-TxConfig
import asyncio

app = Celery('rmcp_tasks')

class MCP-TxTask(Task):
    """MCP-Txサポート付きベースタスク"""
    
    _rmcp = None
    
    @property
    def rmcp(self):
        if MCP-TxTask._rmcp is None:
            # MCP-Txを初期化
            config = MCP-TxConfig(
                default_timeout_ms=60000,  # バックグラウンドタスクでは長いタイムアウト
                retry_policy=RetryPolicy(max_attempts=5)
            )
            
            mcp_session = self._create_mcp_session()
            MCP-TxTask._rmcp = FastMCP-Tx(mcp_session, config)
            
            # 初期化
            loop = asyncio.new_event_loop()
            loop.run_until_complete(MCP-TxTask._rmcp.initialize())
        
        return MCP-TxTask._rmcp

@app.task(base=MCP-TxTask, bind=True)
def process_data_async(self, data_id: str):
    """MCP-Txを使用するCeleryタスク"""
    # イベントループで実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # データダウンロード
        download_result = loop.run_until_complete(
            self.rmcp.call_tool(
                "download_data",
                {"data_id": data_id},
                idempotency_key=f"celery-download-{data_id}"
            )
        )
        
        # データ処理
        process_result = loop.run_until_complete(
            self.rmcp.call_tool(
                "process_data",
                {"file_path": download_result.result["path"]},
                idempotency_key=f"celery-process-{data_id}"
            )
        )
        
        return {
            "status": "completed",
            "result": process_result.result,
            "total_attempts": (
                download_result.rmcp_meta.attempts +
                process_result.rmcp_meta.attempts
            )
        }
    
    except Exception as e:
        # Celeryがリトライを処理
        self.retry(exc=e, countdown=60)
```

## データベース統合

### SQLAlchemy統合

```python
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class MCP-TxOperation(Base):
    """データベースでMCP-Tx操作を追跡"""
    
    __tablename__ = 'rmcp_operations'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String(64), unique=True, index=True)
    tool_name = Column(String(128))
    arguments = Column(JSON)
    idempotency_key = Column(String(128), index=True)
    attempts = Column(Integer)
    status = Column(String(32))
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class DatabaseTrackedMCP-Tx:
    """データベース追跡付きMCP-Tx"""
    
    def __init__(self, app: FastMCP-Tx, db_url: str):
        self.app = app
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    async def call_tool_tracked(
        self,
        name: str,
        arguments: dict,
        **kwargs
    ):
        """データベース追跡付きでツールを呼び出し"""
        session = self.Session()
        
        # 既存の操作をチェック
        idempotency_key = kwargs.get('idempotency_key')
        if idempotency_key:
            existing = session.query(MCP-TxOperation).filter_by(
                idempotency_key=idempotency_key,
                status='completed'
            ).first()
            
            if existing:
                # キャッシュされた結果を返す
                return MCP-TxResult(
                    result=existing.result,
                    rmcp_meta=MCP-TxResponse(
                        ack=True,
                        processed=True,
                        duplicate=True,
                        request_id=existing.request_id,
                        attempts=existing.attempts
                    )
                )
        
        # 操作レコードを作成
        operation = MCP-TxOperation(
            tool_name=name,
            arguments=arguments,
            idempotency_key=idempotency_key,
            status='pending'
        )
        session.add(operation)
        session.commit()
        
        try:
            # 操作を実行
            result = await self.app.call_tool(name, arguments, **kwargs)
            
            # レコードを更新
            operation.request_id = result.rmcp_meta.request_id
            operation.attempts = result.rmcp_meta.attempts
            operation.status = 'completed'
            operation.result = result.result
            operation.completed_at = datetime.utcnow()
            session.commit()
            
            return result
            
        except Exception as e:
            operation.status = 'failed'
            operation.completed_at = datetime.utcnow()
            session.commit()
            raise
        
        finally:
            session.close()
```

## メッセージキュー統合

### RabbitMQ統合

```python
import aio_pika
import json

class RabbitMQMCP-Tx:
    """非同期処理用RabbitMQ付きMCP-Tx"""
    
    def __init__(self, app: FastMCP-Tx, amqp_url: str):
        self.app = app
        self.amqp_url = amqp_url
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """RabbitMQに接続"""
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        self.channel = await self.connection.channel()
        
        # キューを宣言
        self.request_queue = await self.channel.declare_queue(
            'rmcp_requests',
            durable=True
        )
        self.response_queue = await self.channel.declare_queue(
            'rmcp_responses',
            durable=True
        )
    
    async def enqueue_tool_call(
        self,
        name: str,
        arguments: dict,
        correlation_id: str
    ):
        """非同期処理用にツール呼び出しをキューに入れる"""
        message = {
            'tool_name': name,
            'arguments': arguments,
            'correlation_id': correlation_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                correlation_id=correlation_id,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key='rmcp_requests'
        )
    
    async def process_queue(self):
        """キューされたツール呼び出しを処理"""
        async with self.request_queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    
                    try:
                        # ツール呼び出しを実行
                        result = await self.app.call_tool(
                            data['tool_name'],
                            data['arguments']
                        )
                        
                        # レスポンスを送信
                        response = {
                            'correlation_id': data['correlation_id'],
                            'success': True,
                            'result': result.result,
                            'metadata': {
                                'request_id': result.rmcp_meta.request_id,
                                'attempts': result.rmcp_meta.attempts
                            }
                        }
                        
                    except Exception as e:
                        response = {
                            'correlation_id': data['correlation_id'],
                            'success': False,
                            'error': str(e)
                        }
                    
                    # レスポンスを公開
                    await self.channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(response).encode(),
                            correlation_id=data['correlation_id']
                        ),
                        routing_key='rmcp_responses'
                    )
```

## クラウドプロバイダー統合

### AWS Lambda統合

```python
# lambda_handler.py
import json
import asyncio
from rmcp import FastMCP-Tx, MCP-TxConfig

# 接続再利用のためハンドラー外で初期化
rmcp_app = None

def get_rmcp_app():
    """MCP-Txアプリを取得または作成"""
    global rmcp_app
    if rmcp_app is None:
        # Lambda環境用に設定
        config = MCP-TxConfig(
            default_timeout_ms=25000,  # Lambdaタイムアウトバッファ
            retry_policy=RetryPolicy(
                max_attempts=2,  # クイックリトライ
                base_delay_ms=500
            )
        )
        
        # MCPセッションを作成（実装固有）
        mcp_session = create_lambda_mcp_session()
        rmcp_app = FastMCP-Tx(mcp_session, config)
        
        # 初期化
        loop = asyncio.new_event_loop()
        loop.run_until_complete(rmcp_app.initialize())
    
    return rmcp_app

def lambda_handler(event, context):
    """MCP-Tx付きAWS Lambdaハンドラー"""
    tool_name = event.get('tool_name')
    arguments = event.get('arguments', {})
    idempotency_key = event.get('idempotency_key')
    
    if not tool_name:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'tool_nameが必要'})
        }
    
    try:
        # MCP-Txアプリを取得
        app = get_rmcp_app()
        
        # ツール呼び出しを実行
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            app.call_tool(
                tool_name,
                arguments,
                idempotency_key=idempotency_key
            )
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'result': result.result,
                'metadata': {
                    'request_id': result.rmcp_meta.request_id,
                    'attempts': result.rmcp_meta.attempts,
                    'duplicate': result.rmcp_meta.duplicate,
                    'remaining_time_ms': context.get_remaining_time_in_millis()
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
```

## 統合のベストプラクティス

### 1. 接続管理

```python
class ConnectionPool:
    """MCP-Tx接続を効率的に管理"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections = []
        self.available = asyncio.Queue(maxsize=max_connections)
    
    async def acquire(self) -> FastMCP-Tx:
        """プールから接続を取得"""
        if not self.connections:
            # 初期接続を作成
            for _ in range(self.max_connections):
                app = await self._create_connection()
                self.connections.append(app)
                await self.available.put(app)
        
        return await self.available.get()
    
    async def release(self, app: FastMCP-Tx):
        """接続をプールに戻す"""
        await self.available.put(app)
    
    async def _create_connection(self) -> FastMCP-Tx:
        """新しいMCP-Tx接続を作成"""
        mcp_session = await create_mcp_session()
        app = FastMCP-Tx(mcp_session)
        await app.initialize()
        return app
```

### 2. エラーハンドリング

```python
class IntegrationErrorHandler:
    """統合用の統一エラーハンドリング"""
    
    @staticmethod
    async def safe_call(app: FastMCP-Tx, tool_name: str, arguments: dict):
        """包括的なエラーハンドリング付きの安全なツール呼び出し"""
        try:
            return await app.call_tool(tool_name, arguments)
        
        except ConnectionError:
            # ネットワーク問題 - リトライの可能性
            logger.error("接続エラー", exc_info=True)
            raise
        
        except TimeoutError:
            # 操作タイムアウト - 冪等性をチェック
            logger.warning(f"{tool_name}の呼び出しでタイムアウト")
            raise
        
        except ValueError as e:
            # バリデーションエラー - リトライしない
            logger.error(f"{tool_name}の無効な引数: {e}")
            raise
        
        except Exception as e:
            # 不明なエラー - ログして再発生
            logger.error(f"{tool_name}での予期しないエラー", exc_info=True)
            raise
```

### 3. 統合テスト

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_rmcp_app():
    """MCP-Txでのテスト用フィクスチャ"""
    app = AsyncMock(spec=FastMCP-Tx)
    
    # 成功レスポンスをモック
    app.call_tool.return_value = MCP-TxResult(
        result={"status": "success"},
        rmcp_meta=MCP-TxResponse(
            ack=True,
            processed=True,
            duplicate=False,
            attempts=1,
            request_id="test-123"
        )
    )
    
    return app

async def test_integration(mock_rmcp_app):
    """統合をテスト"""
    result = await your_integration_function(mock_rmcp_app)
    
    assert result["success"] is True
    mock_rmcp_app.call_tool.assert_called_once()
```

## 関連ドキュメント

- [高度な例](advanced_jp.md) - 複雑な使用パターン  
- [設定ガイド](../configuration_jp.md) - 統合固有の設定
- [はじめに](../getting-started_jp.md) - 基本セットアップ

---

**前へ**: [高度な例](advanced_jp.md) | **次へ**: [API リファレンス](../api/rmcp-session_jp.md)