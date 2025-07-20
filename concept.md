# Reliable MCP (RMCP)

> **A reliability layer for MCP tool calls**  
> MCP opens the connection. RMCP guarantees the tools actually executed.

[![Tests](https://github.com/Daku-on/reliable-MCP-draft/actions/workflows/test.yml/badge.svg)](https://github.com/Daku-on/reliable-MCP-draft/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

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

## 🚀 FastRMCP - Decorator-Based Python SDK

**FastRMCP** provides a decorator-based interface similar to FastMCP, making it easy to add RMCP reliability features to your tools:

```python
from rmcp import FastRMCP, RetryPolicy

# Wrap your existing MCP session
app = FastRMCP(mcp_session)

@app.tool()
async def reliable_file_writer(path: str, content: str) -> dict:
    """Write file with automatic retry and idempotency."""
    with open(path, 'w') as f:
        f.write(content)
    return {"path": path, "size": len(content)}

@app.tool(retry_policy=RetryPolicy(max_attempts=5))
async def critical_api_call(url: str, data: dict) -> dict:
    """Critical API call with aggressive retry policy."""
    response = await http_client.post(url, json=data)
    return response.json()

# Use with automatic RMCP reliability
async with app:
    result = await app.call_tool("reliable_file_writer", {
        "path": "/tmp/data.json", 
        "content": json.dumps(data)
    })
    
    print(f"ACK: {result.rmcp_meta.ack}")           # True - confirmed receipt
    print(f"Processed: {result.rmcp_meta.processed}") # True - actually executed
    print(f"Attempts: {result.rmcp_meta.attempts}")    # How many retries needed
```

### Installation

```bash
# Clone the repository
git clone https://github.com/Daku-on/reliable-MCP-draft.git
cd reliable-MCP-draft/rmcp-python

# Install dependencies
uv install

# Run tests
uv run pytest tests/ -v
```

### Key Features

✅ **Decorator-based API** - Simple `@app.tool()` decorator for any function  
✅ **Automatic retry** - Configurable retry policies with exponential backoff  
✅ **Request deduplication** - Prevents duplicate tool executions  
✅ **ACK/NACK guarantees** - Know when tools actually executed  
✅ **Thread-safe** - Concurrent tool calls with proper async patterns  
✅ **Type-safe** - Comprehensive type hints throughout  
✅ **Cross-platform** - Works with both asyncio and trio  

## Protocol Specification

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

### ✅ **Python SDK (FastRMCP)** - Production Ready
- **Decorator-based API** - `@app.tool()` pattern similar to FastMCP
- **Input validation** - Type checking and error handling
- **Thread safety** - Concurrent execution with proper async patterns
- **Deep copy protection** - Configuration immutability
- **Comprehensive testing** - 31 test cases covering edge cases
- **Cross-platform async** - Support for both asyncio and trio

### 🚧 **Core Protocol Features**
- **P0 (MVP)**: ✅ ACK/NACK + basic retry + request deduplication  
- **P1**: 🔄 Advanced retry policies + transaction management
- **P2**: 📋 Large file chunking + monitoring + production features

### 📁 **Project Structure**
```
reliable-MCP-draft/
├── rmcp-python/           # Python SDK implementation
│   ├── src/rmcp/
│   │   ├── fastrmcp.py   # Decorator-based API
│   │   ├── session.py    # Core RMCP session
│   │   └── types.py      # Type definitions
│   ├── tests/            # Comprehensive test suite
│   └── examples/         # Usage examples
├── design.md             # System design documentation
└── requirements.md       # Requirements specification
```

[View full specification →](./rmcp-python/README.md)

## Why You Need This

Autonomous agents require **step-by-step reliability**:

1. **File operations**: "Did the file actually get written?"
2. **External APIs**: "Did the webhook actually fire?"  
3. **Multi-step workflows**: "Which steps completed? Which failed?"
4. **Error recovery**: "Should I retry this operation?"

RMCP makes these questions answerable at the protocol level.

### 🎯 **Real-World Use Cases**

```python
# Data processing pipeline with reliability
@app.tool(retry_policy=RetryPolicy(max_attempts=3))
async def process_large_file(file_path: str) -> dict:
    """Process file with automatic retry on failure."""
    data = await load_and_validate(file_path)
    result = await expensive_computation(data)
    await save_results(result)
    return {"processed": len(data), "output_path": result.path}

# Multi-step workflow with individual tool reliability
async def reliable_workflow():
    # Step 1: Download data (with retry)
    download_result = await app.call_tool("download_data", {"url": data_url})
    
    # Step 2: Process data (with different retry policy)  
    process_result = await app.call_tool("process_large_file", {
        "file_path": download_result.result["path"]
    })
    
    # Step 3: Upload results (with idempotency)
    upload_result = await app.call_tool("upload_results", {
        "data": process_result.result
    }, idempotency_key=f"upload-{process_result.rmcp_meta.request_id}")
    
    # Full audit trail available
    return {
        "download_attempts": download_result.rmcp_meta.attempts,
        "process_attempts": process_result.rmcp_meta.attempts,
        "upload_duplicate": upload_result.rmcp_meta.duplicate,
        "total_success": all(r.rmcp_meta.ack for r in [download_result, process_result, upload_result])
    }
```

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

### FastRMCP Python SDK - デコレータベースAPI

FastMCPと同様のデコレータAPIで、簡単にRMCP信頼性機能を追加：

```python
from rmcp import FastRMCP, RetryPolicy

app = FastRMCP(mcp_session)

@app.tool()
async def reliable_file_writer(path: str, content: str) -> dict:
    """自動リトライ・冪等性付きファイル書込み"""
    with open(path, 'w') as f:
        f.write(content)
    return {"path": path, "size": len(content)}

@app.tool(retry_policy=RetryPolicy(max_attempts=5))
async def critical_api_call(url: str, data: dict) -> dict:
    """重要なAPI呼び出し（積極的リトライ設定）"""
    response = await http_client.post(url, json=data)
    return response.json()

# 自動RMCP信頼性機能付きで使用
async with app:
    result = await app.call_tool("reliable_file_writer", {
        "path": "/tmp/data.json", 
        "content": json.dumps(data)
    })
    
    print(result.rmcp_meta.ack)       # True - サーバー受信確認
    print(result.rmcp_meta.processed) # True - 実際に実行された
    print(result.rmcp_meta.attempts)  # 必要だったリトライ回数
```

### 実装済み機能

#### ✅ Python SDK (FastRMCP) - 本番利用可能
- **デコレータベースAPI** - `@app.tool()`でツールを簡単登録
- **入力検証** - 型チェックとエラーハンドリング
- **スレッドセーフ** - 並行実行対応の適切な非同期パターン
- **Deep Copy保護** - 設定変更の防止
- **包括的テスト** - 31テストケースでエッジケースもカバー
- **クロスプラットフォーム** - asyncio/trio両対応

#### 🚧 コアプロトコル機能
- **ACK/NACK必須**: 受信・処理の明示的確認
- **重複実行防止**: `request_id`による冪等性保証  
- **自動再送**: 設定可能な再送ポリシー
- **実行追跡**: トランザクションID + ステータス管理

### MCP互換性

- 既存MCPコードはそのまま動作
- RMCP対応時のみ信頼性機能が有効化
- `experimental`フィールドでの機能ネゴシエーション

**MCPがツールへの道を開いた。RMCPはそのツールが確実に動作したことを保証する。**
