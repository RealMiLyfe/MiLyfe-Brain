"""MiLyfe Brain — Direct Ollama Client Utility."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


async def call_ollama(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
) -> Dict[str, Any]:
    """Direct call to Ollama /api/chat.

    Returns: {"content": str, "model": str, "prompt_tokens": int, "completion_tokens": int}
    """
    model = model or settings.default_heavy_model

    async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )

        if resp.status_code != 200:
            logger.error("ollama_error", status=resp.status_code, body=resp.text[:500])
            raise RuntimeError(f"Ollama error: HTTP {resp.status_code}")

        data = resp.json()
        return {
            "content": data.get("message", {}).get("content", ""),
            "model": data.get("model", model),
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_duration_ms": data.get("total_duration", 0) / 1_000_000,
        }


async def list_models() -> List[Dict[str, Any]]:
    """List available Ollama models."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{settings.ollama_base_url}/api/tags")
        if resp.status_code != 200:
            return []
        return resp.json().get("models", [])


async def check_model_available(model: str) -> bool:
    """Check if a specific model is available."""
    models = await list_models()
    return any(m.get("name", "").startswith(model) for m in models)
