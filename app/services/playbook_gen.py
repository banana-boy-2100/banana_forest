from app.services.claude_client import complete
from app.services.vector_store import search_knowledge

PLAYBOOK_SYSTEM = """あなたは営業プレイブック作成の専門家です。
提供された営業ナレッジを元に、実践的で使いやすい営業プレイブックを作成してください。

プレイブックの構成:
1. シナリオ概要（どんな場面で使うか）
2. 事前準備チェックリスト
3. トーク流れ（フェーズ別）
4. よくある反論と切り返し集
5. クロージングフレーズ集
6. 注意点・落とし穴

Markdown形式で、実際の営業担当者が使いやすいように書いてください。
具体的な言い回し・スクリプト例を多く含めてください。"""


async def generate_playbook(scenario: str, n_knowledge: int = 10) -> str:
    relevant = search_knowledge(scenario, n_results=n_knowledge)

    if not relevant:
        knowledge_context = "（まだナレッジが蓄積されていません。一般的な営業ベストプラクティスを元に作成します）"
    else:
        items = "\n\n".join(
            f"【{r['metadata'].get('category', '')}】{r['metadata'].get('title', '')}\n{r['content']}"
            for r in relevant
        )
        knowledge_context = f"以下の社内ナレッジを参照:\n\n{items}"

    user_msg = f"シナリオ: {scenario}\n\n{knowledge_context}\n\nこのシナリオ向けの営業プレイブックを作成してください。"

    return await complete(
        messages=[{"role": "user", "content": user_msg}],
        system=PLAYBOOK_SYSTEM,
        max_tokens=8192,
    )


REALTIME_SYSTEM = """あなたは商談中の営業担当者をサポートするAIアドバイザーです。
蓄積された社内ナレッジを元に、現在の商談状況に対して即座に実践的なアドバイスを提供します。

回答は簡潔に3点以内で、すぐに使える言い回し・アクションを提示してください。"""


async def get_realtime_suggestion(situation: str) -> str:
    relevant = search_knowledge(situation, n_results=5)

    if not relevant:
        knowledge_context = "（関連ナレッジなし）"
    else:
        items = "\n".join(
            f"・{r['metadata'].get('title', '')}: {r['content'][:200]}..."
            for r in relevant
        )
        knowledge_context = f"関連ナレッジ:\n{items}"

    user_msg = f"現在の商談状況:\n{situation}\n\n{knowledge_context}\n\n今すぐ使えるアドバイスをください。"

    return await complete(
        messages=[{"role": "user", "content": user_msg}],
        system=REALTIME_SYSTEM,
        max_tokens=1024,
    )
