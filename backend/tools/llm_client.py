"""Direct Ollama LLM utility for MiLyfe Brain.

Provides a simple async interface to the Ollama /api/generate endpoint.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

# Default timeout for LLM generation requests
LLM_TIMEOUT = 120.0


async def llm_generate(
    prompt: str,
    model: Optional[str] = None,
) -> str:
    """Generate text using the Ollama LLM API.

    Args:
        prompt: The prompt to send to the model.
        model: Model name to use. Defaults to settings.default_light_model.

    Returns:
        The generated text response from the model.
    """
    target_model = model or settings.default_light_model
    url = f"{settings.ollama_base_url}/api/generate"

    logger.info(
        "llm_generate: model=%s prompt_len=%d",
        target_model,
        len(prompt),
    )

    payload = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.ConnectError:
        return (
            f"[ERROR] Cannot connect to Ollama at {settings.ollama_base_url}. "
            "Ensure the Ollama server is running."
        )
    except httpx.TimeoutException:
        return (
            f"[ERROR] LLM request timed out after {LLM_TIMEOUT}s. "
            "The model may be loading or the prompt too long."
        )
    except httpx.HTTPStatusError as exc:
        return f"[ERROR] Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:500]}"
    except httpx.HTTPError as exc:
        return f"[ERROR] HTTP error communicating with Ollama: {exc}"

    data = response.json()
    generated_text = data.get("response", "")

    if not generated_text:
        return "[ERROR] Ollama returned an empty response."

    logger.info(
        "llm_generate: completed (%d chars generated)",
        len(generated_text),
    )
    return generated_text
