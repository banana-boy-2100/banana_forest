import json
from app.services.claude_client import complete

EXTRACT_SYSTEM = """あなたは営業の暗黙知を形式知化する専門家AIです。
提供されたテキスト（商談メモ、議事録、インタビュー、チャットログなど）から、
営業担当者が持つ暗黙知・ノウハウを抽出・構造化してください。

以下のカテゴリで分類してください:
- objection_handling: 反論・懸念への対処法
- rapport_building: 関係構築のテクニック
- needs_discovery: ニーズ・課題の引き出し方
- closing: クロージング手法
- product_knowledge: 製品・サービス知識
- competitor_info: 競合情報・差別化ポイント
- process: 営業プロセス・フロー
- other: その他の知見

必ずJSON配列で返してください。各要素は以下の形式:
{
  "title": "知見のタイトル（簡潔に）",
  "content": "詳細な説明（具体的な言い回し、手順、背景も含む）",
  "category": "カテゴリ名",
  "tags": ["タグ1", "タグ2"]
}
"""


async def extract_knowledge_from_text(text: str, source_hint: str = "") -> list[dict]:
    hint = f"\n\n情報源のヒント: {source_hint}" if source_hint else ""
    user_msg = f"以下のテキストから営業の暗黙知を抽出してください:{hint}\n\n---\n{text}\n---"

    raw = await complete(
        messages=[{"role": "user", "content": user_msg}],
        system=EXTRACT_SYSTEM,
        max_tokens=8192,
    )

    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return []


TRANSCRIBE_SYSTEM = """あなたは営業トランスクリプトのアナリストです。
与えられた音声文字起こしテキストから、営業担当者と顧客のやり取りを分析し、
有益な営業ノウハウを抽出してください。

フォーマットはJSON配列で返してください。"""


async def extract_from_transcript(transcript: str) -> list[dict]:
    return await extract_knowledge_from_text(transcript, "音声文字起こし・商談録音")


CHAT_SYSTEM = """あなたはSlack/チャットログのアナリストです。
営業チームのチャットログから、有益な営業ノウハウ・ベストプラクティスを抽出してください。
日常会話は無視し、明確な知見・テクニック・情報のみを抽出してください。

フォーマットはJSON配列で返してください。"""


async def extract_from_chat(chat_log: str) -> list[dict]:
    return await extract_knowledge_from_text(chat_log, "Slack/チャットログ")
