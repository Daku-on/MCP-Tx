# Reliable MCP (RMCP)

> **A reliability layer for MCP tool calls**  
> MCP opens the connection. RMCP guarantees the tools actually executed.

## The Problem

You know this pain point with MCP:

```python
# Standard MCP call
result = await session.call_tool("file_writer", {"path": "/tmp/data.json", "content": data})
# Did it actually write? Is the file there? If it failed, do we retry?
# What if the network dropped mid-write?
```

MCP gives you JSON-RPC with tools, but no **delivery guarantees**. For autonomous agents that need to coordinate multi-step workflows, this isn't enough.

## The Solution

RMCP adds exactly what MCP is missing:

```python
# RMCP call with guarantees
result = await rmcp_session.call_tool("file_writer", {"path": "/tmp/data.json", "content": data})

# You now know:
print(result.ack)          # True - server confirmed receipt
print(result.processed)    # True - tool actually executed  
print(result.final_status) # "completed" | "failed" | "timeout"
print(result.attempts)     # How many retries were needed
```

## Core Features

| MCP Pain Point | RMCP Solution | Implementation |
|----------------|---------------|----------------|
| **Silent failures** | Required ACK/NACK | `_meta.rmcp.ack: true/false` |
| **Duplicate execution** | Request deduplication | `_meta.rmcp.request_id` + idempotency |
| **No retry logic** | Automatic retry with backoff | Configurable retry policy |
| **Can't track progress** | Request lifecycle tracking | Transaction IDs + status objects |

## Quick Start

RMCP uses MCP's `experimental` capabilities for backward compatibility:

```typescript
// Client capability negotiation
const params = {
  capabilities: {
    experimental: {
      rmcp: { version: "0.1.0", features: ["ack", "retry", "idempotency"] }
    }
  }
}

// RMCP-enhanced request
const request = {
  method: "tools/call",
  params: {
    name: "file_reader",
    arguments: { path: "/data/input.txt" },
    _meta: {
      rmcp: {
        expect_ack: true,
        request_id: "rmcp-1234567890",
        idempotency_key: "read_input_file_v1"
      }
    }
  }
}

// Response with guarantees
{
  "result": { /* tool output */ },
  "_meta": {
    "rmcp": {
      "ack": true,
      "processed": true,
      "duplicate": false,
      "attempts": 1
    }
  }
}
```

## Architecture

RMCP wraps your existing MCP session:

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Agent     │────▶│   RMCP Wrapper   │────▶│    Tool     │
│   (Client)  │◀────│  + MCP Session   │◀────│  (Server)   │
└─────────────┘     └──────────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │   Reliability  │
                    │ • ACK tracking │
                    │ • Retry logic  │
                    │ • Deduplication│
                    └─────────────────┘
```

## Backward Compatibility

- **100% MCP compatible**: Falls back to standard MCP when RMCP isn't supported
- **Opt-in only**: RMCP features activate only when both sides support it
- **No breaking changes**: Existing MCP tools work unchanged

```python
# Same code works with both MCP and RMCP servers
session = RMCPSession(mcp_session)  # Wraps existing session
result = await session.call_tool("any_tool", args)  # Auto-detects capabilities
```

## Implementation Status

- **P0 (MVP)**: ✅ ACK/NACK + basic retry + request deduplication  
- **P1**: 🚧 Advanced retry policies + transaction management
- **P2**: 📋 Large file chunking + monitoring + production features

[View full specification →](./mvp-spec.md)

## Why You Need This

Autonomous agents require **step-by-step reliability**:

1. **File operations**: "Did the file actually get written?"
2. **External APIs**: "Did the webhook actually fire?"  
3. **Multi-step workflows**: "Which steps completed? Which failed?"
4. **Error recovery**: "Should I retry this operation?"

RMCP makes these questions answerable at the protocol level.

---

**MCP opened the door to tools. RMCP makes sure you can trust what happened next.**

---

## 日本語概要

**Reliable MCP (RMCP)** は、MCPツール呼び出しに信頼性を追加するプロトコル拡張です。

### 解決する問題

MCPでツールを呼び出しても「本当に実行されたか」「失敗した場合の対処」が分からない：

```python
# 標準MCPの問題
result = await session.call_tool("file_writer", {"path": "/tmp/data.json", "content": data})
# ファイルは書けた？ネットワークエラーで途中で落ちた？再実行すべき？
```

### RMCPの解決策

```python
# RMCP - 実行保証付き
result = await rmcp_session.call_tool("file_writer", {"path": "/tmp/data.json", "content": data})

print(result.ack)          # True - サーバーが受信確認
print(result.processed)    # True - ツールが実際に実行された
print(result.final_status) # "completed" | "failed" | "timeout"
```

### 主要機能

- **ACK/NACK必須**: 受信・処理の明示的確認
- **重複実行防止**: `request_id`による冪等性保証  
- **自動再送**: 設定可能な再送ポリシー
- **実行追跡**: トランザクションID + ステータス管理

### MCP互換性

- 既存MCPコードはそのまま動作
- RMCP対応時のみ信頼性機能が有効化
- `experimental`フィールドでの機能ネゴシエーション

**MCPがツールへの道を開いた。RMCPはそのツールが確実に動作したことを保証する。**
