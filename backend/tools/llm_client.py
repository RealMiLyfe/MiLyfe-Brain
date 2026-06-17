"""
MiLyfe Brain - LLM Client

Ollama API client for model inference.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from config import settings


async def call_ollama(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    stream: bool = False,
) -> Dict[str, Any]:
    """Call Ollama chat completion API.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        model: Model name (defaults to settings.default_heavy_model).
        temperature: Sampling temperature (0.0 - 2.0).
        max_tokens: Maximum tokens to generate.
        stream: Whether to stream the response.

    Returns:
        Dict with 'content', 'model', 'total_duration', 'prompt_eval_count',
        'eval_count', and 'done' keys.
    """
    model = model or settings.default_heavy_model
    base_url = settings.ollama_base_url.rstrip("/")

    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
            if stream:
                return await _call_ollama_stream(client, base_url, payload)

            response = await client.post(
                f"{base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "content": data.get("message", {}).get("content", ""),
                "model": data.get("model", model),
                "total_duration": data.get("total_duration", 0),
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
                "done": data.get("done", True),
            }

    except httpx.ConnectError:
        return {
            "content": "",
            "model": model,
            "error": f"Cannot connect to Ollama at {base_url}. Is it running?",
            "done": True,
        }
    except httpx.HTTPStatusError as e:
        return {
            "content": "",
            "model": model,
            "error": f"Ollama API error: {e.response.status_code} - {e.response.text[:200]}",
            "done": True,
        }
    except Exception as e:
        return {
            "content": "",
            "model": model,
            "error": f"LLM call failed: {type(e).__name__}: {e}",
            "done": True,
        }


async def _call_ollama_stream(
    client: httpx.AsyncClient,
    base_url: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Handle streaming Ollama response.

    Returns aggregated result dict.
    """
    content_parts: List[str] = []
    final_data: Dict[str, Any] = {}

    async with client.stream(
        "POST",
        f"{base_url}/api/chat",
        json=payload,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue

            if chunk.get("message", {}).get("content"):
                content_parts.append(chunk["message"]["content"])

            if chunk.get("done", False):
                final_data = chunk
                break

    return {
        "content": "".join(content_parts),
        "model": final_data.get("model", payload.get("model", "")),
        "total_duration": final_data.get("total_duration", 0),
        "prompt_eval_count": final_data.get("prompt_eval_count", 0),
        "eval_count": final_data.get("eval_count", 0),
        "done": True,
    }


async def list_models() -> List[Dict[str, Any]]:
    """List available models from Ollama.

    Returns:
        List of model info dicts with 'name', 'size', 'modified_at' keys.
    """
    base_url = settings.ollama_base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = []
            for model in data.get("models", []):
                models.append({
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                    "digest": model.get("digest", "")[:12],
                })
            return models

    except Exception as e:
        return [{"error": f"Failed to list models: {type(e).__name__}: {e}"}]


async def check_model_available(model: str) -> bool:
    """Check if a specific model is available in Ollama.

    Args:
        model: Model name to check.

    Returns:
        True if model is available, False otherwise.
    """
    models = await list_models()
    if models and "error" in models[0]:
        return False
    return any(m.get("name", "").startswith(model.split(":")[0]) for m in models)
