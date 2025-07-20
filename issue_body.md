### 日本語 (Japanese)

**背景:**
`session.py` の `_sanitize_error_message` メソッドは、エラーログに機密情報が漏洩するのを防ぐための重要なセキュリティ機能です。しかし、現在の正規表現パターンは限定的であり、一般的な認証情報（例: `API_KEY`, `Authorization` ヘッダー）を見逃す可能性があります。

**提案:**

このサニタイズ処理を強化し、より包括的なセキュリティ対策とすることを提案します。

**具体的な改善案:**

1.  **正規表現パターンの拡充:** OWASPの推奨などを参考に、`API_KEY`, `Authorization`, `access_token` といった、より広範な機密情報のパターンを検出できるように正規表現リストを更新します。
2.  **モジュール化とテストの徹底:** このサニタイズ機能を独立した関数またはモジュールとして切り出し、多様なエッジケースをカバーする単体テストを作成して、カバレッジを100%にします。これにより、機能の信頼性が保証されます。

この改善により、意図しない情報漏洩のリスクを大幅に低減し、ライブラリのセキュリティを強化します。

---

### 英語 (English)

**Background:**
The `_sanitize_error_message` method in `session.py` is a critical security feature designed to prevent sensitive information from leaking into error logs. However, the current set of regular expression patterns is limited and may fail to catch common credentials (e.g., `API_KEY`, `Authorization` headers).

**Proposal:**

I propose enhancing this sanitization process to make it more comprehensive and secure.

**Specific Improvements:**

1.  **Expand Regex Patterns:** Update the list of regular expressions to detect a broader range of sensitive patterns, referencing security guidelines from sources like OWASP. This should include patterns for `API_KEY`, `Authorization`, `access_token`, and more.
2.  **Modularize and Thoroughly Test:** Extract the sanitization logic into a standalone function or module and create dedicated unit tests that cover a wide variety of edge cases, aiming for 100% test coverage. This will ensure the reliability of this critical function.

These improvements will significantly reduce the risk of unintentional information disclosure and strengthen the library's overall security posture.