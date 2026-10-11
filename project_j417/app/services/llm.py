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

from app.core.config import LLM_API_KEY, LLM_MODEL, LLM_PROVIDER


def complete(prompt: str, system: str = "", max_tokens: int = 1500) -> str:
    if LLM_PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=LLM_API_KEY)
        resp = client.messages.create(
            model=LLM_MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    if LLM_PROVIDER == "gemini":
        from google import genai
        client = genai.Client(api_key=LLM_API_KEY)
        resp = client.models.generate_content(
            model=LLM_MODEL, contents=prompt,
            config={"system_instruction": system},
        )
        return resp.text

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")