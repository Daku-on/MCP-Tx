# CLAUDE.md - Project Development Insights

## Python Development Best Practices

### Package Management
- **Use `uv add package-name` instead of manually editing pyproject.toml**
  - User feedback: "pyprojectはベタ書きせずにuv add package-nameってして育ててくといいよ"
  - This ensures proper dependency resolution and lock file updates

### File Naming Conventions
- **Japanese documentation files should use underscore format: `filename_jp.md`**
  - User correction: "ファイル名は hoge_jp.mdにしてね"
  - Not `.jp.md` format - use `_jp.md` suffix

### Directory Organization
- **Documentation should be organized by language in separate directories**
  - Preferred structure: `docs/en/` and `docs/jp/`
  - User request: "ドキュメント系はルートは以下のdocs/en docs/jpにまとめてほしい"
  - Keep language-specific files properly segregated

## Development Workflow

### Testing and CI
- **Always run local CI checks before pushing**
  - Use `uv run pytest` for test execution
  - Run linting and type checking locally: `uv run ruff check`, `uv run mypy`
  - User feedback: "一応ローカルでもCI通して残ってるものがないか確認しといて"

### Cross-platform Async Support
- **Use `anyio` for asyncio/trio compatibility**
  - Replace `asyncio.sleep` with `anyio.sleep`
  - Replace `asyncio.gather` with `anyio.create_task_group()`
  - Add trio to dev dependencies for testing both async backends

### Git and PR Management
- **Create focused PRs for different types of changes**
  - Separate PRs for lint fixes, test fixes, and new features
  - User approach: Created separate PRs for ruff fixes (#8) and failing tests (#9)

## Technical Implementation Notes

### RMCP Session Management
- **Idempotency requires returning copies, not mutating cached results**
  - Bug discovered: mutating cached results affected subsequent calls
  - Solution: Always return deep copies of cached data

### Error Handling
- **Timeout handling needs careful async context management**
  - Move cancellation checks outside context managers
  - Ensure proper cleanup of async resources

### Documentation Standards
- **Comprehensive bilingual documentation approach**
  - Create complete English documentation first
  - Follow with equivalent Japanese versions
  - Include practical examples and troubleshooting guides
  - Structure: README, getting-started, architecture, migration, FAQ, troubleshooting, API reference, examples

## Project-Specific Insights

### RMCP Architecture
- **Reliability layer for MCP (Model Context Protocol)**
  - Implements idempotency with LRU cache + TTL
  - Exponential backoff retry with jitter
  - ACK/NACK delivery guarantees
  - Transaction lifecycle management

### Testing Strategy
- **Use anyio for cross-platform async testing**
  - Supports both asyncio and trio backends
  - Essential for library compatibility
  - Run comprehensive test suite covering all async scenarios

---

## 日本語要約

このプロジェクトで学んだ重要な開発知見：

**Python開発のベストプラクティス:**
- `uv add package-name`でパッケージ管理（pyproject.toml直接編集はNG）
- 日本語ドキュメントファイル名は`filename_jp.md`形式
- ドキュメントは`docs/en/`と`docs/jp/`で言語別整理

**開発ワークフロー:**
- プッシュ前にローカルでCI確認必須
- 異なる種類の修正は別々のPRで管理
- anyioで非同期互換性確保（asyncio/trio両対応）

**技術実装のポイント:**
- RMCPの冪等性実装ではキャッシュ結果のコピーを返却
- タイムアウト処理は非同期コンテキスト管理に注意
- 包括的な英語・日本語バイリンガルドキュメント作成

**プロジェクト固有の知見:**
- RMCP = MCP (Model Context Protocol) の信頼性レイヤー
- 冪等性、指数バックオフ、配信保証を実装
- anyioによるクロスプラットフォーム非同期テスト戦略