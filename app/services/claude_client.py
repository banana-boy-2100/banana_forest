import anthropic
from app.core.config import settings

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def complete(
    messages: list[dict],
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    client = get_client()
    kwargs = dict(
        model=settings.claude_model,
        max_tokens=max_tokens,
        messages=messages,
    )
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)
    return response.content[0].text
