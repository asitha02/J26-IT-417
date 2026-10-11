import anthropic
from app.core.config import LLM_API_KEY, LLM_MODEL

_client = anthropic.Anthropic(api_key=LLM_API_KEY)


def complete(prompt: str, system: str = "", max_tokens: int = 1500) -> str:
    resp = _client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text