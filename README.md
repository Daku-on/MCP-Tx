# Reliable MCP (RMCP) README

## 概要 (Overview)
**Reliable MCP（RMCP）**は、LLM が外部ツールやデータソースとやり取りを行う際に、「処理を依頼した」だけで終わるのではなく、「処理が実際に行われ、成功・失敗を確認できた」状態まで到達できるようにする通信拡張プロトコルです。  
MCP は接続性に優れた軽量プロトコルですが、実運用に必要な信頼性（信号の通過確認、順序制御、失敗時の復旧など）を担保するレイヤーが欠けています。RMCP はそのギャップを補完します。

## 背景 (Problem Statement)
現在の MCP（Model Context Protocol）は JSON-RPC 2.0 ベースで構築されており、LLM と外部ツール間の機能的な接続は可能です。しかし、以下のような「通信の保証」に関する要件は MCP 自体では定義されていません：

- メッセージの順序保証
- 再送制御とリトライ
- 配信確認（ACK/NACK）
- トランザクションレベルでの成功可否判定
- コンテキスト消失前の確実な処理確認

この結果、エージェントによる複数ステップの処理や、外部ツールとの確実な連携を求める場面では、アプリケーション側に複雑な制御ロジックの実装が求められていました。

## RMCP が提供するもの (RMCP Features)

| 機能                         | 説明                                                                 |
|------------------------------|----------------------------------------------------------------------|
| 順序制御（Ordering）        | ステップ1→2→3などの処理を順番通りに実行させるための制御             |
| 再送（Retry）               | 通信・処理失敗時に再実行可能な仕組み                                |
| 確認応答（ACK/NACK）        | 受信側が処理完了を明示的に通知、応答がない限り次の処理に進まない     |
| フロー制御（Flow Control） | トークン数やAPIリクエスト制限に応じて適切なペース配分を行う           |
| 再送戦略（Retransmission Strategy） | 前回の失敗を踏まえて別ルートを選択するような判断ロジック        |

これらにより、LLM が外部ツールとやり取りする際の「完了保証付きの処理」が可能となります。

## RMCP の意義 (Why It Matters)
従来の LLM は「入力に対して出力を返す」応答器として振る舞っていましたが、今後のエージェント的 LLM には以下のような責務が求められます：

- 処理の成否を確認する
- 途中で失敗してもリカバリする
- 複数のタスクを信頼性を持って連携させる

RMCP は、そうしたエージェントのための“信頼性の基盤（≒TCP）”となることを目的としています。

## 今後の展開 (Status)
現在は設計・提案段階です。MCP 互換プロトタイプの開発も進行中であり、コミュニティフィードバックを歓迎しています。

---

## Overview
**Reliable MCP (RMCP)** extends the Model Context Protocol to introduce reliability—confirming not just that a tool call was sent, but that it was delivered, executed, and acknowledged.

## Problem Statement
MCP is a clean, JSON-RPC 2.0–based interface for LLM-to-tool communication. But it lacks the transmission guarantees needed to build robust, multi-step agent workflows:

- Message ordering
- Retry mechanisms
- Acknowledgement signaling (ACK/NACK)
- Transaction-level status
- Visibility into delivery/completion state

As LLMs evolve from passive responders to active operators, these guarantees become foundational.

## RMCP Features

| Capability               | Description                                                              |
|--------------------------|---------------------------------------------------------------------------|
| Ordering                 | Ensures multi-step processes run in intended sequence                     |
| Retry                    | Automatic re-attempts for failed or dropped tasks                         |
| ACK/NACK                 | Confirmed delivery and execution before continuing                        |
| Flow control             | Regulates pacing based on token budget or API quotas                      |
| Retransmission strategy  | Chooses alternative routes or retries with adjustments after failure       |

RMCP enables LLMs to reliably interact with external systems in a way that mirrors how TCP guarantees delivery in low-level networks.

## Why It Matters
Next-generation agents are expected to operate services, recover from transient failures, and maintain consistent execution plans across tools.

Like TCP underpins HTTP, RMCP can underpin dependable orchestration for autonomous agents.

## Status
Early design draft. MCP-compatible prototype in progress.

---

**MCP solved connection. RMCP solves trust.**
