"""Direct Ollama Client Utility — for non-agent LLM calls."""

import httpx
from config import settings


async def llm_generate(prompt: str, model: str = None, temperature: float = 0.7) -> str:
    """Direct LLM call via Ollama."""
    model = model or settings.default_heavy_model

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


async def llm_chat(messages: list[dict], model: str = None, temperature: float = 0.7) -> str:
    """Multi-turn chat via Ollama."""
    model = model or settings.default_heavy_model

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
