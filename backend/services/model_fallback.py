"""Model Fallback — Fallback chain for LLM calls (httpx, no langchain)."""

from typing import Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class ModelFallback:
    """Try models in order until one succeeds."""

    def __init__(self):
        self._fallback_chain = [
            settings.default_heavy_model,
            settings.default_light_model,
            "llama3.1:8b",
            "phi3:mini",
        ]

    async def generate(
        self,
        messages: list[dict],
        preferred_model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> dict:
        """Try models in fallback order until success."""
        chain = [preferred_model] + self._fallback_chain if preferred_model else self._fallback_chain
        seen = set()

        for model in chain:
            if model in seen:
                continue
            seen.add(model)

            try:
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
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "model": model,
                            "content": data.get("message", {}).get("content", ""),
                            "tokens": data.get("eval_count", 0),
                        }
                    else:
                        logger.warning("Model failed", model=model, status=resp.status_code)
            except Exception as e:
                logger.warning("Model unreachable", model=model, error=str(e))

        raise RuntimeError("All models in fallback chain failed")


# Global instance
model_fallback = ModelFallback()
