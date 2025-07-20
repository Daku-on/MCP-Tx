# Tool Share: MCP-Tx, A Transaction Layer for MCP

Hey everyone,

Just wanted to share a tool and an idea I've been working on: treating MCP operations like transactions.

I'm calling it **MCP-Tx** for now.
**GitHub:** [https://github.com/daku-on/reliable-MCP-draft](https://github.com/daku-on/reliable-MCP-draft)

-----

### Overview

**MCP-Tx** is a lightweight wrapper for any MCP session. It adds a layer of transactional guarantees **without needing any server-side changes.**

In this context, "transactional" means providing:

-   ✅ **Retries for Atomicity:** Ensures an operation eventually completes as a single unit.
-   ✅ **Idempotency for Consistency:** Prevents duplicate processing to keep the system state correct.
-   ✅ **ACK/NACK for Durability:** Confirms an operation has been successfully committed.
-   ✅ **Trace IDs for... well, Transaction IDs:** Allows for end-to-end tracking of an operation's lifecycle.

MCP-Tx is more than just a client-side utility. It's a protocol that enables a new level of collaboration between clients and servers. It even allows for treating **human operators as a 'reliable server' in the workflow**, breaking down the barrier between automated and human-in-the-loop tasks.

### The "Human as a Server" Concept

This is the core idea that makes MCP-Tx powerful. You can treat automated services and human approval steps with the exact same interface, applying full reliability guarantees to both.

```mermaid
flowchart LR
    subgraph "MCP-Tx Client (Orchestrator)"
        direction LR
        A[call_tool("analyze_data")]
        B[call_tool("human_approval")]
        C[call_tool("send_report")]
        A --> B --> C
    end

    subgraph "MCP-Tx Servers"
        direction TB
        Server1[Automated Server]
        Server2[Human Operator (via UI)]
    end

    A -- MCP-Tx Request --> Server1
    B -- MCP-Tx Request --> Server2
    C -- MCP-Tx Request --> Server1
```

In this architecture, when `call_tool("human_approval")` is invoked, the MCP-Tx session simply waits for an "ACK" that is triggered by a human clicking an "Approve" button in a UI. This elegantly applies **idempotency, retries, and timeouts to human tasks.**

```python
# Workflow Orchestration
print("Starting analysis by AI...")
await mcp_tx_session.call_tool("analyze_data", {"source": "data.csv"})

print("Waiting for user approval...")
# This call waits for a human to click "Approve" in a UI.
# It can time out or be retried just like any other tool call.
approval_result = await mcp_tx_session.call_tool(
    "human_approval",
    {"message": "Generate a report from this analysis?"},
    timeout_ms=3600000 # 1 hour timeout
)

if approval_result.ack:
    print("Approved! Sending report.")
    await mcp_tx_session.call_tool("send_report", {})
```

### Backstory: The Vision for Autonomous Agents

The idea started from the vision that **AI agents should be more autonomous.**

For an agent to operate independently, it needs to handle common failures like flaky APIs gracefully. Instead of just giving up, what if it could treat its operations like database transactions—ensuring they either complete successfully or fail cleanly after a set number of attempts?

This library is a simple exploration of that concept. It provides the toolkit to give agents that transactional safety, allowing them to recover from transient failures on their own.

Dropping it here in case anyone else is thinking about how to build more robust, autonomous agents. It's not a formal proposal, just sharing an idea.

---

### For Server Developers: Why You Should Support MCP-Tx

MCP-Tx isn't just for clients. Adopting it on the server-side makes your service more robust, efficient, and easier to operate.

#### 1. Reduce Load and Protect Resources
-   **Prevent Expensive Recomputations**: With **idempotency keys**, you can cache the results of costly operations (like LLM calls or complex queries). If the same request comes again, you return the cached result, saving significant compute resources and API credits.
-   **Smarter Rate Limiting**: The client's built-in exponential backoff and jitter already prevents request storms. In the future, servers could even send back metadata like "retry in 5 seconds" to dynamically manage load.

#### 2. Simplify Operations and Debugging
-   **End-to-End Tracking**: By logging the **transaction and request IDs** sent by MCP-Tx, you gain instant observability. A single ID allows you to trace an operation across the entire system, drastically cutting down on debugging time.
-   **Simplified Error Handling**: For transient errors like a temporary database disconnect, you no longer need complex internal retry logic. Just return an error with a `retryable` flag, and let the client handle it. This keeps your server-side code cleaner.

#### 3. Enable Advanced Capabilities
-   **Asynchronous Tasks**: The ACK/NACK mechanism is perfect for long-running jobs. Acknowledge the request immediately (`ACK`), process it in the background, and let the client poll for the result using the request ID. This avoids HTTP timeouts entirely.
-   **Request Cancellation**: A future extension could allow clients to send a "cancel" signal for an in-flight request ID, allowing your server to free up resources from abandoned tasks.

By adopting MCP-Tx, you're not just supporting a client library; you're participating in a **shared language for building more resilient and efficient distributed systems.**

---

### Strategic Summary: The Path Forward

The core concept—**injecting a reliability layer into the established MCP ecosystem**—is powerful. To maximize its value and drive adoption, the project focuses on four key areas:

1.  **For the Ecosystem, Not Just the Client**: Position MCP-Tx as a **symbiotic protocol** that benefits both clients and servers by clearly articulating the server-side advantages.
2.  **Production-Ready by Design**: The architecture must account for real-world failures. This means moving beyond in-memory state management to a **pluggable, persistent model** (e.g., using Redis) for tracking long-running agent workflows.
3.  **Developer Experience First**: The API should be robust and easy to debug. We will provide **sensible defaults for idempotency key generation**, offer **debugging hooks** like `on_retry`, and use **Enums instead of magic strings** to promote type-safe development.
4.  **Clear Adoption Path**: Ensure seamless interoperability through a **well-defined capability negotiation** process and transparent fallback behavior when connecting to non-MCP-Tx-aware servers.

By focusing on these areas, MCP-Tx can evolve from a powerful idea into an indispensable tool for the entire AI development community.

---
---

# ツール共有: MCP-Tx、MCPのためのトランザクションレイヤー

皆さん、

私が取り組んできたツールとアイデアを共有したいと思います。それは、MCPの操作をトランザクションのように扱うというものです。

今のところ **MCP-Tx** と呼んでいます。
**GitHub:** [https://github.com/daku-on/reliable-MCP-draft](https://github.com/daku-on/reliable-MCP-draft)

-----

### 概要

**MCP-Tx** は、あらゆるMCPセッションを軽量にラップするライブラリです。**サーバー側の変更を一切必要とせずに**、トランザクションのような保証のレイヤーを追加します。

ここでの「トランザクション的」とは、以下の機能を提供することを意味します：

-   ✅ **原子性のためのリトライ**: 操作が最終的に単一のユニットとして完了することを保証します。
-   ✅ **一貫性のための冪等性**: 重複した処理を防ぎ、システムの整合性を保ちます。
-   ✅ **永続性のためのACK/NACK**: 操作が正常にコミットされたことを確認します。
-   ✅ **トランザクションIDとしてのトレースID**: 操作のライフサイクルをエンドツーエンドで追跡できます。

MCP-Txは単なるクライアントサイドのユーティリティではありません。クライアントとサーバー間の新しいレベルの協調を可能にするプロトコルです。さらには、**人間のオペレーターをワークフロー上の「信頼できるサーバー」として扱う**ことさえ可能にし、自動化と人間参加型のタスクとの間の障壁を取り払います。

### 「サーバーとしての人間」というコンセプト

これこそがMCP-Txを強力にする中心的なアイデアです。自動化されたサービスと人間による承認ステップを全く同じインターフェースで扱うことができ、両方に完全な信頼性保証を適用できます。

```mermaid
flowchart LR
    subgraph "MCP-Tx クライアント (オーケストレーター)"
        direction LR
        A[call_tool("analyze_data")]
        B[call_tool("human_approval")]
        C[call_tool("send_report")]
        A --> B --> C
    end

    subgraph "MCP-Tx サーバー"
        direction TB
        Server1[自動化サーバー]
        Server2[人間のオペレーター (UI経由)]
    end

    A -- MCP-Tx リクエスト --> Server1
    B -- MCP-Tx リクエスト --> Server2
    C -- MCP-Tx リクエスト --> Server1
```

このアーキテクチャでは、`call_tool("human_approval")` が呼び出されると、MCP-TxセッションはUI上の「承認」ボタンが人間によってクリックされることでトリガーされる「ACK」を単純に待ちます。これにより、**人間のタスクにも冪等性、リトライ、タイムアウトがエレガントに適用されます。**

```python
# ワークフローのオーケストレーション
print("AIによる分析を開始...")
await mcp_tx_session.call_tool("analyze_data", {"source": "data.csv"})

print("ユーザーの承認を待っています...")
# この呼び出しは、人間がUIで「承認」をクリックするのを待ちます。
# 他のツール呼び出しと同様に、タイムアウトしたりリトライしたりできます。
approval_result = await mcp_tx_session.call_tool(
    "human_approval",
    {"message": "この分析からレポートを生成しますか？"},
    timeout_ms=3600000 # 1時間のタイムアウト
)

if approval_result.ack:
    print("承認されました！レポートを送信します。")
    await mcp_tx_session.call_tool("send_report", {})
```

### 背景: 自律型エージェントへのビジョン

このアイデアは、**AIエージェントはもっと自律的であるべきだ**というビジョンから始まりました。

エージェントが独立して動作するためには、不安定なAPIのような一般的な障害を適切に処理する必要があります。単に諦めるのではなく、データベースのトランザクションのように操作を扱うことができたらどうでしょうか？つまり、設定された試行回数の後、成功裏に完了するか、クリーンに失敗するかのどちらかです。

このライブラリは、そのコンセプトの単純な探求です。エージェントにトランザクションの安全性を提供し、一時的な障害から自力で回復できるようにするためのツールキットを提供します。

より堅牢で自律的なエージェントの構築について考えている他の方々のために、ここに共有します。これは正式な提案ではなく、単なるアイデアの共有です。

---

### サーバー開発者の方へ: なぜMCP-Txをサポートすべきか

MCP-Txはクライアントのためだけのものではありません。サーバーサイドで採用することで、あなたのサービスはより堅牢で、効率的で、運用しやすくなります。

#### 1. 負荷の軽減とリソースの保護
-   **高価な再計算の防止**: **冪等性キー**により、高コストな操作（LLM呼び出しや複雑なクエリなど）の結果をキャッシュできます。同じリクエストが再度来た場合、キャッシュした結果を返すだけで済み、計算リソースとAPIクレジットを大幅に節約できます。
-   **賢いレートリミット**: クライアントに組み込まれた指数バックオフとジッターが、リクエストの殺到を防ぎます。将来的には、サーバーが「5秒後にリトライして」のようなメタデータを返すことで、動的に負荷を管理することも可能になります。

#### 2. 運用とデバッグの簡素化
-   **エンドツーエンドの追跡**: MCP-Txが送信する**トランザクションIDとリクエストID**をログに記録するだけで、システムの可観測性が飛躍的に向上します。単一のIDで操作を追跡でき、デバッグ時間を大幅に短縮できます。
-   **エラーハンドリングの簡略化**: 一時的なデータベース切断のようなエラーに対して、複雑なリトライロジックを自前で実装する必要がなくなります。`retryable`フラグを付けてエラーを返すだけで、クライアントが適切に処理します。

#### 3. 高度な機能の実現
-   **非同期タスク**: ACK/NACKメカニズムは、時間のかかるジョブに最適です。リクエストを即座にACKで受け付け、バックグラウンドで処理し、クライアントは後でリクエストIDを使って結果を取得できます。
-   **リクエストのキャンセル**: 将来的に、クライアントが進行中のリクエストIDに対して「キャンセル」を送信できるように拡張すれば、不要になったタスクからリソースを解放できます。

MCP-Txを採用することは、単にクライアントライブラリをサポートするだけでなく、**より回復力があり効率的な分散システムを構築するための共通言語**に参加することを意味します。

---

### 戦略的サマリー: 前進への道

**確立されたMCPエコシステムに信頼性のレイヤーを注入する**という中心的なコンセプトは強力です。その価値を最大化し、採用を促進するために、プロジェクトは4つの主要分野に焦点を当てています：

1.  **クライアントのためだけでなく、エコシステムのために**: サーバーサイドの利点を明確に打ち出すことで、MCP-Txをクライアントとサーバー双方に利益をもたらす**共生プロトコル**として位置づけます。
2.  **本番環境を想定した設計**: 現実世界の障害を考慮に入れる必要があります。これは、インメモリの状態管理を超え、**プラグイン可能で永続的なモデル**（例：Redisを使用）へと移行し、長時間実行されるエージェントのワークフローを追跡することを意味します。
3.  **開発者体験を第一に**: APIは堅牢でデバッグしやすいものであるべきです。**冪等性キー生成のための賢明なデフォルト**を提供し、`on_retry`のような**デバッグ用フック**を提供し、**マジックストリングの代わりにEnumを使用**して、型安全な開発を促進します。
4.  **明確な採用パス**: **明確に定義された能力ネゴシエーション**プロセスと、MCP-Tx非対応サーバーに接続する際の透明なフォールバック動作を通じて、シームレスな相互運用性を確保します。

これらの分野に焦点を当てることで、MCP-Txは強力なアイデアから、AI開発コミュニティ全体にとって不可欠なツールへと進化することができます。