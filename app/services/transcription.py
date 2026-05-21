from __future__ import annotations
import os
import tempfile
from pathlib import Path
from app.core.config import settings

SUPPORTED_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".ogg", ".oga", ".flac", ".mpeg", ".mpga"}


async def transcribe_audio_file(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio using OpenAI Whisper API."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY が未設定です。.env ファイルに設定してください。")

    import openai
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise ValueError(f"非対応フォーマット: {suffix}。対応形式: {', '.join(SUPPORTED_FORMATS)}")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, f),
                language="ja",
            )
        return response.text
    finally:
        os.unlink(tmp_path)
