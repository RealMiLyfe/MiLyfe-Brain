"""MiLyfe Brain — Model Fallback Chain (httpx, no langchain)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class ModelFallback:
    """Tries models in order until one succeeds."""

    def __init__(self):
        self._fallback_chain = [
            settings.default_heavy_model,
            settings.default_light_model,
            "phi3:mini",
            "llama3.1:8b",
        ]

    async def call_with_fallback(
        self,
        messages: List[Dict[str, str]],
        preferred_model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Call LLM with automatic fallback on failure."""
        chain = [preferred_model] + self._fallback_chain if preferred_model else self._fallback_chain
        # Deduplicate while preserving order
        seen = set()
        chain = [m for m in chain if m and m not in seen and not seen.add(m)]

        last_error = None
        for model in chain:
            try:
                result = await self._try_model(model, messages, temperature)
                if result:
                    return result
            except Exception as e:
                last_error = e
                logger.warning("model_fallback", model=model, error=str(e))
                continue

        raise RuntimeError(f"All models failed. Last error: {last_error}")

    async def _try_model(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> Optional[Dict[str, Any]]:
        """Try a single model."""
        async with httpx.AsyncClient(timeout=settings.agent_timeout) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )

            if resp.status_code != 200:
                return None

            data = resp.json()
            content = data.get("message", {}).get("content", "")
            if not content:
                return None

            return {
                "content": content,
                "model": model,
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            }

    async def check_availability(self) -> Dict[str, bool]:
        """Check which models are available."""
        results = {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    available = {m.get("name", "") for m in models}
                    for model in self._fallback_chain:
                        results[model] = any(model in a for a in available)
        except Exception:
            pass
        return results


# Singleton
model_fallback = ModelFallback()
