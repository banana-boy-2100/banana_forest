from __future__ import annotations
import json
from app.services.claude_client import complete
from app.services.vector_store import search_knowledge

ENRICH_SYSTEM = """あなたは営業ナレッジの専門家です。
既存の営業知見を、関連する追加情報を踏まえてより詳細・実践的に深化させてください。

出力形式: JSON
{
  "title": "改善されたタイトル",
  "content": "より詳細・実践的な内容（具体的なセリフ例・状況・注意点を含む）",
  "tags": ["タグ"]
}
"""

SYNTHESIZE_SYSTEM = """あなたは営業ナレッジの戦略アナリストです。
蓄積された営業知見を分析し、重要なパターン・インサイト・ベストプラクティスを
分かりやすい形にまとめてください。

Markdown形式で、以下を含めてください:
1. 主要パターン（3〜5個）
2. 共通する成功要因
3. 注意すべき落とし穴
4. アクション可能な推奨事項
"""


async def enrich_knowledge_item(title: str, content: str, category: str) -> dict:
    related = search_knowledge(f"{title} {content[:100]}", n_results=5)

    related_context = "\n".join(
        f"- {r['metadata'].get('title', '')}: {r['content'][:200]}"
        for r in related
        if r["metadata"].get("title") != title
    )

    prompt = f"""以下の知見を深化・充実させてください:

【タイトル】{title}
【カテゴリ】{category}
【現在の内容】
{content}

【関連する蓄積知見】
{related_context or "（関連知見なし）"}

より実践的で具体的な内容に発展させてください。"""

    raw = await complete(
        messages=[{"role": "user", "content": prompt}],
        system=ENRICH_SYSTEM,
        max_tokens=4096,
    )

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"title": title, "content": content, "tags": []}


async def synthesize_category(category: str, knowledge_items: list[dict]) -> str:
    items_text = "\n\n".join(
        f"【{item['title']}】\n{item['content']}"
        for item in knowledge_items[:20]
    )

    prompt = f"""カテゴリ「{category}」の以下の営業知見を総合分析してください:\n\n{items_text}"""

    return await complete(
        messages=[{"role": "user", "content": prompt}],
        system=SYNTHESIZE_SYSTEM,
        max_tokens=4096,
    )
