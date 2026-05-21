import json
from app.services.claude_client import complete

INTERVIEW_SYSTEM = """あなたは営業の暗黙知を引き出すプロのインタビュアーAIです。
営業担当者が長年の経験で培ったノウハウ・勘所・コツを、丁寧な対話を通じて引き出します。

インタビューの進め方:
1. まず担当者の経験や得意分野を把握する
2. 具体的なエピソード（成功体験・失敗体験）を引き出す
3. 「なぜそうしたか」「どう判断したか」を深掘りする
4. 再現可能な形で知識を言語化させる
5. 十分な情報が集まったら、まとめに移る

注意事項:
- 一度に質問は1〜2個まで
- 「なぜ」「どうやって」「具体的には」を多用する
- 抽象的な答えには必ず具体例を求める
- 否定せず、引き出すことに集中する
- 日本語で自然な会話調で話す

会話の冒頭では自己紹介し、インタビューの目的（暗黙知の形式知化）を簡潔に説明してから始めてください。"""


async def get_interview_response(
    messages: list[dict],
    interviewee_name: str,
    topic: str | None = None,
) -> str:
    topic_hint = f"本日のテーマ: {topic}" if topic else "テーマは自由（担当者の得意分野・経験から探る）"
    system = f"{INTERVIEW_SYSTEM}\n\nインタビュー対象者: {interviewee_name}さん\n{topic_hint}"
    return await complete(messages=messages, system=system, max_tokens=1024)


SYNTHESIS_SYSTEM = """あなたは営業ナレッジ整理の専門家です。
インタビューの会話記録から、形式知として価値ある知見を抽出・構造化してください。

JSON配列で出力してください。各要素:
{
  "title": "知見タイトル",
  "content": "詳細説明（具体的な言い回しや手順を含む）",
  "category": "objection_handling|rapport_building|needs_discovery|closing|product_knowledge|competitor_info|process|other",
  "tags": ["タグ"]
}"""


async def synthesize_interview(messages: list[dict], interviewee_name: str) -> list[dict]:
    transcript = "\n".join(
        f"{'AI' if m['role'] == 'assistant' else interviewee_name}: {m['content']}"
        for m in messages
    )
    user_msg = f"以下のインタビュー記録から営業の暗黙知を抽出してください:\n\n{transcript}"

    raw = await complete(
        messages=[{"role": "user", "content": user_msg}],
        system=SYNTHESIS_SYSTEM,
        max_tokens=8192,
    )

    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return []
