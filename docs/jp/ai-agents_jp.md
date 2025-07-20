# RMCPでAIエージェントを構築する

このガイドでは、FastRMCPデコレータを使用して信頼性の高いAIエージェントを構築する方法を実演します。堅牢なエラーハンドリングと配信保証を必要とするマルチステップワークフローに焦点を当てています。

## 概要: スマートリサーチアシスタント

複数のAIツールをRMCP信頼性機能と組み合わせて包括的なリサーチを実行する**スマートリサーチアシスタント**を構築します。

### エージェント機能

| ツール | 目的 | RMCPのメリット |
|------|-----|-------------|
| **Web検索** | 関連するソースを発見 | API障害時のリトライ |
| **コンテンツ分析** | 要約と洞察の抽出 | 冪等な処理 |
| **ファクトチェック** | 情報の正確性を検証 | ACK/NACK確認 |
| **レポート生成** | 構造化された出力を作成 | トランザクション追跡 |
| **知識保存** | リサーチ結果を永続化 | 重複防止 |

### AIエージェントでRMCPを使う理由

AIエージェントには以下が伴うことが多い：
- **外部API呼び出し** が予期せず失敗する可能性
- **長時間実行ワークフロー** で回復が必要
- **高価な操作** を重複させるべきでない
- **複雑な状態** で追跡が必要

RMCPは自動リトライ、冪等性、配信保証でこれらの課題に対処します。

## アーキテクチャ

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  リサーチ       │    │   スマートリサーチ │    │   AIサービス    │
│  リクエスト     │───▶│   アシスタント   │───▶│   (OpenAI等)    │
└─────────────────┘    │   (FastRMCP)     │    └─────────────────┘
                       └──────────────────┘              │
                                │                        │
                       ┌────────▼────────┐              │
                       │ RMCP信頼性      │◀─────────────┘
                       │ • リトライ論理  │
                       │ • 冪等性        │
                       │ • ACK/NACK      │
                       │ • 追跡          │
                       └─────────────────┘
```

## 実装

### 1. コアエージェントセットアップ

```python
from rmcp import FastRMCP, RetryPolicy, RMCPConfig
import openai
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Any

# AIワークロード用の設定
config = RMCPConfig(
    default_timeout_ms=30000,  # AI APIは遅い場合がある
    max_concurrent_requests=5,  # レート制限の考慮
    enable_request_logging=True,
    deduplication_window_ms=600000  # リサーチタスクに10分
)

# リサーチアシスタントを作成
research_agent = FastRMCP(mcp_session, config=config, name="スマートリサーチアシスタント")
```

### 2. Web検索ツール

```python
@research_agent.tool(
    retry_policy=RetryPolicy(
        max_attempts=3,
        base_delay_ms=2000,
        backoff_multiplier=2.0
    ),
    timeout_ms=15000,
    idempotency_key_generator=lambda args: f"search-{hash(args['query'])}"
)
async def web_search(query: str, num_results: int = 5) -> Dict[str, Any]:
    """失敗時の自動リトライでWeb情報を検索"""
    
    async with aiohttp.ClientSession() as session:
        # SerpAPI、Bing、Google Custom Searchを使用
        search_url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "num": num_results,
            "api_key": os.getenv("SERPAPI_KEY")
        }
        
        async with session.get(search_url, params=params) as response:
            if response.status != 200:
                raise Exception(f"検索API エラー: {response.status}")
            
            data = await response.json()
            
            results = []
            for result in data.get("organic_results", []):
                results.append({
                    "title": result.get("title"),
                    "url": result.get("link"),
                    "snippet": result.get("snippet"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return {
                "query": query,
                "results": results,
                "total_found": len(results)
            }
```

### 3. コンテンツ分析ツール

```python
@research_agent.tool(
    retry_policy=RetryPolicy(
        max_attempts=5,  # AI APIは不安定な場合がある
        base_delay_ms=1000
    ),
    idempotency_key_generator=lambda args: f"analyze-{hash(args['content'][:100])}"
)
async def analyze_content(content: str, focus_areas: List[str] = None) -> Dict[str, Any]:
    """信頼性保証付きでAIを使用してコンテンツを分析・要約"""
    
    if not focus_areas:
        focus_areas = ["key_insights", "credibility", "relevance"]
    
    prompt = f"""
    以下のコンテンツを分析し、{', '.join(focus_areas)}について洞察を提供してください
    
    コンテンツ: {content[:2000]}...
    
    以下の項目で構造化された分析を提供：
    1. 主要な洞察（箇条書き）
    2. 信頼性評価（1-10点）
    3. クエリとの関連性（1-10点）
    4. 要約（2-3文）
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        analysis = response.choices[0].message.content
        
        return {
            "original_length": len(content),
            "analysis": analysis,
            "focus_areas": focus_areas,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # RMCPが自動的にリトライ
        raise Exception(f"AI分析に失敗: {str(e)}")
```

### 4. ファクトチェックツール

```python
@research_agent.tool(
    retry_policy=RetryPolicy(max_attempts=3),
    timeout_ms=20000,
    idempotency_key_generator=lambda args: f"factcheck-{hash(args['claim'])}"
)
async def fact_check(claim: str, sources: List[str] = None) -> Dict[str, Any]:
    """信頼できるソースに対して情報を検証"""
    
    verification_prompt = f"""
    提供されたソースを使用して以下の主張をファクトチェックしてください：
    
    主張: {claim}
    
    ソース: {json.dumps(sources) if sources else "提供なし"}
    
    以下を提供：
    1. 検証ステータス: VERIFIED（検証済み）, DISPUTED（議論中）, UNVERIFIED（未検証）
    2. 信頼度スコア（1-10）
    3. 支持する証拠
    4. 矛盾する証拠（あれば）
    5. さらなる調査の推奨
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": verification_prompt}],
            max_tokens=400
        )
        
        verification = response.choices[0].message.content
        
        return {
            "claim": claim,
            "verification": verification,
            "sources_checked": len(sources) if sources else 0,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"ファクトチェックに失敗: {str(e)}")
```

### 5. レポート生成ツール

```python
@research_agent.tool(
    timeout_ms=25000,
    idempotency_key_generator=lambda args: f"report-{args['research_id']}"
)
async def generate_research_report(
    research_id: str,
    search_results: List[Dict],
    analyses: List[Dict],
    fact_checks: List[Dict],
    query: str
) -> Dict[str, Any]:
    """包括的なリサーチレポートを生成"""
    
    report_prompt = f"""
    以下に基づいて包括的なリサーチレポートを作成してください：
    
    元のクエリ: {query}
    リサーチID: {research_id}
    
    検索結果: {len(search_results)}個のソースを発見
    コンテンツ分析: {len(analyses)}個を分析
    ファクトチェック: {len(fact_checks)}個の主張を検証
    
    以下の構造でレポートを生成：
    1. エグゼクティブサマリー
    2. 主要な発見
    3. ソース分析
    4. 信頼性評価
    5. 行動への推奨
    6. さらなる調査領域
    
    明確なセクションでMarkdown形式で作成。
    """
    
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{"role": "user", "content": report_prompt}],
            max_tokens=1000
        )
        
        report_content = response.choices[0].message.content
        
        # 構造化レポートを作成
        report = {
            "research_id": research_id,
            "query": query,
            "generated_at": datetime.utcnow().isoformat(),
            "content": report_content,
            "metadata": {
                "sources_count": len(search_results),
                "analyses_count": len(analyses),
                "fact_checks_count": len(fact_checks)
            },
            "status": "completed"
        }
        
        return report
        
    except Exception as e:
        raise Exception(f"レポート生成に失敗: {str(e)}")
```

### 6. 知識保存ツール

```python
@research_agent.tool(
    idempotency_key_generator=lambda args: f"save-{args['research_id']}"
)
async def save_research(research_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
    """将来の参照用にリサーチ結果を保存"""
    
    # 本番環境では、これはデータベースに保存される
    filename = f"research_{research_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = f"./research_results/{filename}"
    
    os.makedirs("./research_results", exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return {
        "research_id": research_id,
        "saved_to": filepath,
        "saved_at": datetime.utcnow().isoformat(),
        "file_size": os.path.getsize(filepath)
    }
```

## リサーチワークフローのオーケストレーション

### マルチステップリサーチプロセス

```python
class SmartResearchAssistant:
    """RMCP信頼性で完全なリサーチワークフローをオーケストレート"""
    
    def __init__(self, agent: FastRMCP):
        self.agent = agent
        self.research_sessions = {}
    
    async def conduct_research(self, query: str, research_id: str = None) -> Dict[str, Any]:
        """完全なRMCP追跡で包括的なリサーチを実施"""
        
        if not research_id:
            research_id = f"research_{int(datetime.utcnow().timestamp())}"
        
        self.research_sessions[research_id] = {
            "query": query,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "steps": []
        }
        
        try:
            # ステップ1: Web検索
            print(f"🔍 検索中: {query}")
            search_result = await self.agent.call_tool(
                "web_search",
                {"query": query, "num_results": 8},
                idempotency_key=f"search-{research_id}"
            )
            
            self._record_step(research_id, "search", search_result)
            search_data = search_result.result
            
            # ステップ2: 各ソースを分析
            print(f"📊 {len(search_data['results'])}個のソースを分析中")
            analyses = []
            
            for i, source in enumerate(search_data['results']):
                try:
                    analysis_result = await self.agent.call_tool(
                        "analyze_content",
                        {
                            "content": f"{source['title']} {source['snippet']}",
                            "focus_areas": ["関連性", "信頼性", "主要洞察"]
                        },
                        idempotency_key=f"analyze-{research_id}-{i}"
                    )
                    analyses.append(analysis_result.result)
                    self._record_step(research_id, f"analysis_{i}", analysis_result)
                    
                except Exception as e:
                    print(f"⚠️ ソース{i}の分析に失敗: {e}")
                    continue
            
            # ステップ3: 主要な主張をファクトチェック
            print(f"✅ 主要な主張をファクトチェック中")
            fact_checks = []
            
            # ファクトチェック用に分析から主張を抽出
            for i, analysis in enumerate(analyses[:3]):  # 上位3つの分析をチェック
                try:
                    fact_check_result = await self.agent.call_tool(
                        "fact_check",
                        {
                            "claim": analysis["analysis"][:200],  # 分析の最初の部分
                            "sources": [s["url"] for s in search_data['results'][:3]]
                        },
                        idempotency_key=f"factcheck-{research_id}-{i}"
                    )
                    fact_checks.append(fact_check_result.result)
                    self._record_step(research_id, f"factcheck_{i}", fact_check_result)
                    
                except Exception as e:
                    print(f"⚠️ 主張{i}のファクトチェックに失敗: {e}")
                    continue
            
            # ステップ4: 包括的レポートを生成
            print(f"📄 リサーチレポートを生成中")
            report_result = await self.agent.call_tool(
                "generate_research_report",
                {
                    "research_id": research_id,
                    "search_results": search_data['results'],
                    "analyses": analyses,
                    "fact_checks": fact_checks,
                    "query": query
                },
                idempotency_key=f"report-{research_id}"
            )
            
            self._record_step(research_id, "report", report_result)
            report = report_result.result
            
            # ステップ5: 結果を保存
            print(f"💾 リサーチ結果を保存中")
            save_result = await self.agent.call_tool(
                "save_research",
                {
                    "research_id": research_id,
                    "report": report
                },
                idempotency_key=f"save-{research_id}"
            )
            
            self._record_step(research_id, "save", save_result)
            
            # セッションステータスを更新
            self.research_sessions[research_id].update({
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "total_steps": len(self.research_sessions[research_id]["steps"]),
                "final_report": report
            })
            
            return {
                "research_id": research_id,
                "status": "success",
                "report": report,
                "metadata": {
                    "sources_found": len(search_data['results']),
                    "analyses_completed": len(analyses),
                    "fact_checks_performed": len(fact_checks),
                    "total_rmcp_attempts": sum(
                        step["attempts"] for step in self.research_sessions[research_id]["steps"]
                    )
                }
            }
            
        except Exception as e:
            self.research_sessions[research_id].update({
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat()
            })
            raise
    
    def _record_step(self, research_id: str, step_name: str, result):
        """RMCPメタデータで各ステップを記録"""
        self.research_sessions[research_id]["steps"].append({
            "step": step_name,
            "request_id": result.rmcp_meta.request_id,
            "attempts": result.rmcp_meta.attempts,
            "duplicate": result.rmcp_meta.duplicate,
            "ack": result.rmcp_meta.ack,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_research_status(self, research_id: str) -> Dict[str, Any]:
        """リサーチセッションの詳細ステータスを取得"""
        return self.research_sessions.get(research_id, {"error": "リサーチIDが見つかりません"})
```

## 使用例

```python
async def main():
    """スマートリサーチアシスタントの使用例"""
    
    # リサーチアシスタントを初期化
    async with research_agent:
        assistant = SmartResearchAssistant(research_agent)
        
        # リサーチを実施
        research_query = "2024年におけるAIのソフトウェア開発生産性への影響"
        
        try:
            result = await assistant.conduct_research(research_query)
            
            print(f"✨ リサーチが正常に完了しました！")
            print(f"📊 分析されたソース: {result['metadata']['sources_found']}")
            print(f"🔄 総RMCP リトライ試行: {result['metadata']['total_rmcp_attempts']}")
            print(f"📄 レポートが生成・保存されました")
            
            # リサーチレポートを表示
            print("\\n" + "="*50)
            print("リサーチレポート")
            print("="*50)
            print(result['report']['content'])
            
        except Exception as e:
            print(f"❌ リサーチに失敗: {e}")

# リサーチアシスタントを実行
if __name__ == "__main__":
    asyncio.run(main())
```

## AIエージェントでのRMCPの主なメリット

### 1. **AIワークフローの信頼性**

```python
# RMCPなし: 手動エラーハンドリング
try:
    result = await openai_api_call()
except Exception:
    # 手動リトライロジック、保証なし
    pass

# RMCPあり: 自動信頼性
@agent.tool(retry_policy=RetryPolicy(max_attempts=3))
async def ai_analysis(content: str) -> dict:
    # 指数バックオフでの自動リトライ
    return await openai_api_call(content)
```

### 2. **冪等性によるコスト制御**

```python
# 高価なAI API呼び出しの重複を防止
@agent.tool(idempotency_key_generator=lambda args: f"analysis-{hash(args['content'])}")
async def expensive_ai_analysis(content: str) -> dict:
    # 同じコンテンツに対して再度呼び出されることはない
    return await costly_ai_service(content)
```

### 3. **ワークフローの透明性**

```python
# 複雑なAIワークフローのすべてのステップを追跡
for step in research_session["steps"]:
    print(f"ステップ {step['step']}: {step['attempts']}回試行, ACK: {step['ack']}")
```

## ベストプラクティス

### 1. **冪等性を考慮した設計**
- 冪等性キーにコンテンツハッシュを使用
- 可能な場合はAI操作を決定論的にする
- 高価な計算をキャッシュ

### 2. **AI API障害を優雅に処理**
- 異なるAIサービスに適切なリトライポリシーを設定
- AI処理時間を考慮したタイムアウトを使用
- フォールバック戦略を実装

### 3. **監視と最適化**
- リトライ試行と失敗率を追跡
- APIコストと使用パターンを監視
- 実際のパフォーマンスに基づいてリトライポリシーを最適化

### 4. **可観測性のための構造化**
- RMCPメタデータで各ワークフローステップをログ
- デバッグのために中間結果を保存
- 包括的なエラーレポートを実装

## エージェントの拡張

スマートリサーチアシスタントは追加ツールで拡張できます：

- **文書分析** - PDF/文書処理
- **画像分析** - 視覚的コンテンツ理解
- **データ可視化** - チャートとグラフ生成
- **多言語サポート** - 翻訳とローカライゼーション
- **リアルタイム更新** - 継続的リサーチ監視

各新しいツールがRMCPの信頼性機能の恩恵を受け、エージェント全体をより堅牢で本番対応にします。

## 関連ドキュメント

- [高度な例](examples/advanced_jp.md) - 複雑なワークフローパターン
- [設定ガイド](configuration_jp.md) - AIワークロードの最適化
- [パフォーマンスガイド](performance_jp.md) - AIエージェントデプロイメントのスケーリング

---

**前へ**: [統合ガイド](examples/integration_jp.md) | **次へ**: [設定ガイド](configuration_jp.md)