# Reliable MCP (RMCP)

> **A trust layer for agent operations.**  
> MCP opens the connection. RMCP guarantees it actually worked.

---

## Overview

**Reliable MCP (RMCP)** adds a trust layer on top of the Model Context Protocol.  
It ensures that when an agent issues a request to an external tool, **we know if it worked.**

### What it fixes

MCP is great for connecting things, but not for trusting what happened.

| Issue                         | RMCP Solution                                |
|------------------------------|----------------------------------------------|
| Message order                | Sequence numbers                             |
| Silent failure               | ACK/NACK required                            |
| No retry built-in            | Retry strategy configurable                  |
| No tracking                  | Transaction IDs and final status objects     |
| Agent can't know result      | RMCP makes it observable                     |

---

### Relationship to A2A

- A2A is about connecting agents to each other  
- RMCP is about **guaranteeing that what was said actually happened**

| Area         | A2A                                        | RMCP                                    |
|--------------|---------------------------------------------|------------------------------------------|
| Scope        | Agent ↔ Agent                               | Agent ↔ Tool                             |
| Purpose      | Inter-agent comms and capability discovery  | Step-wise trust, retries, observability |
| Layer type   | Dialogue protocol                           | Transport-level reliability              |

---

### Why RMCP?

Future LLM-based agents will be:

- Not just responders
- But autonomous task executors
- Coordinating across tools with retry logic and state awareness

RMCP is how they can do that **safely and observably**.

---

### Status

- Draft stage  
- RFC open  
- Prototype server in development

---

### TL;DR

**MCP opened the pipe.**  
**RMCP makes sure what went in actually came out the other side—and worked.**

---

## 概要（Overview）

Reliable MCP（RMCP）は、LLMが外部ツール・データソースとやり取りを行う際に「通ったつもり」で終わらせず、  
**「実際に通った・完了した」ことをプロトコルレベルで保証する**ための拡張仕様です。

## 背景：MCPの限界

MCP（Model Context Protocol）は JSON-RPC 2.0ベースで設計されており、  
構文的には整っていて、「tool call」や「外部ファイル参照」もできる。  
でも、通信の成否に関しては以下が**保証されていない**：

| 欠落している保証               | 結果                                                |
|------------------------------|-----------------------------------------------------|
| メッセージ順序                | 並列実行がズレても検出できない                    |
| 成功/失敗の確認（ACK/NACK）   | 相手が「やった」と言っても、信じるしかない         |
| 再送戦略                      | 途中で落ちても再実行されない                      |
| 完了ステータス                | 「いつ完了したか」「失敗したか」が追えない        |
| トランザクションの整合性      | tool callが途中で止まっても、次に進んでしまう     |

---

## RMCPが追加するTCP的レイヤー

| 機能                         | 説明                                                                 |
|------------------------------|----------------------------------------------------------------------|
| 順序制御（Ordering）        | ステップの実行順序を保証                                             |
| 再送（Retry）               | タイムアウトや失敗時に自動再送                                       |
| ACK/NACK                    | 完了確認が返ってくるまで次に進まない                                 |
| フロー制御（Flow Control） | トークン数/API制限に応じて送信を調整                                 |
| 再送戦略（Retransmit Policy）| 複数経路や回避手段の選択ロジックを定義                              |

→ つまり、**これはTCP for agents。**

---

## RMCPとA2Aの関係性

- **A2A（Agent2Agent Protocol）**：Agent間の接続・発話・メタ情報の交換を担う（≒通訳）  
- **RMCP**：その会話の**実行結果が“本当に成功したか”を保証する通信制御レイヤー**（≒配達＋配達確認）

| 領域         | A2A                                             | RMCP                                             |
|--------------|--------------------------------------------------|--------------------------------------------------|
| 通信対象     | Agent ⇔ Agent                                    | Agent ⇔ Tool                                     |
| 目的         | 接続、発話、能力発見                             | ステップ実行の信頼性・再送・完了追跡              |
| 層の性質     | 会話・発話のプロトコル                           | 通信信頼性のトランスポートレイヤー               |

---

## RMCPが必要な理由

未来のLLM/エージェントは：

- 単発のレスポンスだけでなく  
- 外部システムとの連携を前提とした構成を取り  
- ステップを踏んで作業し、途中失敗もリカバリする

これを**通信として正しく支える構成**が、RMCP。

---

## 状態（Status）

- 🚧 設計草案フェーズ  
- 🔁 MCP互換の試作サーバ実装中  
- ✉️ コミュニティフィードバック歓迎

---

**MCPは道を開いた。RMCPはその道が本当に通ったかを確かめる。**
