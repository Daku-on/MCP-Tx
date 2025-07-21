# MCP-Tx: A Transaction Layer for the Model Context Protocol

**MCP-Tx** is a lightweight, client-side reliability layer that wraps any MCP session to provide transactional guarantees—like idempotency, retries, and acknowledgments—**without requiring any server-side changes.**

It enables developers to build robust, autonomous AI agents that can gracefully recover from common failures, treating every operation like a database transaction.

**GitHub Repository:** [https://github.com/Daku-on/MCP-Tx](https://github.com/Daku-on/MCP-Tx)

---

## 🚀 Quick Start

Get up and running in under a minute.

**1. Installation**
```bash
# Using uv (recommended)
uv add mcp_tx

# Using pip
pip install mcp_tx
```

**2. Wrap Your Session and Call a Tool**
```python
import asyncio
from mcp_tx import MCPTxSession
from mcp.client.session import ClientSession # Your existing MCP client

async def main():
    # 1. Your existing MCP session setup (replace with your actual session)
    mcp_session = ClientSession(...)

    # 2. Wrap with MCP-Tx for automatic reliability
    async with MCPTxSession(mcp_session) as mcp_tx_session:
        await mcp_tx_session.initialize()

        # 3. Call tools with transactional guarantees
        result = await mcp_tx_session.call_tool(
            "file_reader",
            {"path": "/path/to/data.txt"}
        )

        if result.ack:
            print("✅ Success:", result.result)
            print(f"   (Completed in {result.attempts} attempt(s))")
        else:
            print(f"❌ Failed: {result.mcp_tx_meta.error_message}")

asyncio.run(main())
```

## Key Features

-   ✅ **Retries for Atomicity:** Ensures an operation eventually completes as a single unit.
-   ✅ **Idempotency for Consistency:** Prevents duplicate processing to keep the system state correct.
-   ✅ **ACK/NACK for Durability:** Confirms an operation has been successfully committed.
-   ✅ **Trace IDs for Transaction Tracking:** Allows for end-to-end tracking of an operation's lifecycle.

## 📖 Documentation

-   [**Getting Started**](docs/en/getting-started.md) - A 5-minute guide to get you up and running.
-   [**Architecture Deep Dive**](docs/en/architecture.md) - Understand how MCP-Tx works under the hood.
-   [**Usage Examples**](docs/en/examples/basic.md) - Explore common patterns and use cases.
-   [**Full API Reference**](docs/en/api/mcp-tx-session.md) - Detailed information on all classes and methods.

---

## 💡 The Core Concept: "Human as a Server"

MCP-Tx's unique power lies in its ability to treat **human operators as just another reliable "server"** in a workflow. This elegantly unifies automated and human-in-the-loop tasks under the same architectural model.

```mermaid
flowchart LR
    subgraph "MCP-Tx Client (Orchestrator)"
        direction LR
        A["call_tool('analyze_data')"] --> B["call_tool('human_approval')"] --> C["call_tool('send_report')"]
    end

    subgraph "MCP-Tx Servers"
        direction TB
        Server1[Automated Server (AI/API)]
        Server2[Human Operator (via UI)]
    end

    A -- MCP-Tx Request --> Server1
    B -- MCP-Tx Request --> Server2
    C -- MCP-Tx Request --> Server1
```

When `call_tool("human_approval")` is invoked, the session simply waits for an "ACK" triggered by a human clicking an "Approve" button. This applies **idempotency, retries, and timeouts to human tasks** just as it would to any automated service.

---
---

# (日本語) MCP-Tx: MCPのためのトランザクションレイヤー

**MCP-Tx**は、既存のMCPセッションをラップする軽量なクライアントサイドの信頼性レイヤーです。**サーバー側の変更を一切必要とせず**、冪等性、リトライ、ACK/NACKといったトランザクションのような保証を追加します。

これにより、不安定なAPIからの復旧などを自律的に行える、堅牢なAIエージェントの構築が可能になります。

**GitHubリポジトリ:** [https://github.com/Daku-on/MCP-Tx](https://github.com/Daku-on/MCP-Tx)

---

## 🚀 クイックスタート

1分で使い始めることができます。

**1. インストール**
```bash
# uv（推奨）
uv add mcp_tx

# pip
pip install mcp_tx
```

**2. セッションをラップしてツールを呼び出す**
```python
import asyncio
from mcp_tx import MCPTxSession
from mcp.client.session import ClientSession # 既存のMCPクライアント

async def main():
    # 1. 既存のMCPセッションを準備 (実際のセッションに置き換えてください)
    mcp_session = ClientSession(...)

    # 2. MCP-Txでラップし、信頼性を自動的に付与
    async with MCPTxSession(mcp_session) as mcp_tx_session:
        await mcp_tx_session.initialize()

        # 3. トランザクション保証付きでツールを呼び出す
        result = await mcp_tx_session.call_tool(
            "file_reader",
            {"path": "/path/to/data.txt"}
        )

        if result.ack:
            print("✅ 成功:", result.result)
            print(f"   (試行回数: {result.attempts}回)")
        else:
            print(f"❌ 失敗: {result.mcp_tx_meta.error_message}")

asyncio.run(main())
```

## 主な特徴

-   ✅ **原子性のためのリトライ**: 操作が最終的に一つの単位として完了することを保証します。
-   ✅ **一貫性のための冪等性**: 同じ操作が誤って複数回実行されるのを防ぎ、システムの整合性を保ちます。
-   ✅ **永続性のためのACK/NACK**: 操作がサーバーに確かに届き、処理がコミットされたことを確認します。
-   ✅ **追跡可能性のためのトランザクションID**: 操作のライフサイクルをエンドツーエンドで追跡可能にします。

## 📖 ドキュメント

-   [**スタートガイド**](docs/jp/getting-started_jp.md) - 5分でセットアップを完了するためのガイドです。
-   [**アーキテクチャ解説**](docs/jp/architecture_jp.md) - MCP-Txの内部構造を深く理解します。
-   [**使用例**](docs/jp/examples/basic_jp.md) - 一般的な使い方やパターンを探ります。
-   [**APIリファレンス**](docs/jp/api/mcp-tx-session_jp.md) - 全てのクラスとメソッドの詳細情報。

---

## 💡 コアコンセプト：「サーバーとしての人間」

MCP-Txのユニークで強力な点は、**人間のオペレーターさえもワークフロー上の「信頼できるサーバー」として扱える**ことです。これにより、自動化されたプロセスと人間が介在するタスクを、同じアーキテクチャ上でエレガントに統一できます。

`call_tool("human_approval")`を呼び出すと、セッションはUI上で人間が「承認」ボタンを押すのを、サーバーからの「ACK」として待機します。この仕組みによって、**人間が関わるタスクにも、ごく自然に冪等性やリトライ、タイムアウトといった信頼性が付与される**のです。