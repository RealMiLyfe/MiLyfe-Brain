"""
MiLyfe Brain - Model Fallback Service

Provides resilient LLM calling with automatic fallback through a model chain.
If the primary model fails, it tries the next model in the chain until one succeeds.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelFallback:
    """Handles LLM calls with automatic model fallback chain."""

    def __init__(self) -> None:
        self._fallback_chain: Optional[List[str]] = None

    def _get_chain(self, primary_model: Optional[str] = None) -> List[str]:
        """Build the model fallback chain based on config."""
        from config import settings

        primary = primary_model or settings.default_heavy_model
        chain = [primary]

        # Add fallback models if different from primary
        candidates = [
            settings.default_heavy_model,
            settings.default_light_model,
            settings.premium_model,
        ]
        for candidate in candidates:
            if candidate not in chain:
                chain.append(candidate)

        return chain

    async def call_with_fallback(
        self,
        messages: List[Dict[str, str]],
        primary_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Call LLM with automatic fallback through model chain.

        Tries each model in the chain until one succeeds.
        Returns the first successful response or the last error.

        Args:
            messages: Chat messages to send.
            primary_model: Preferred model to try first.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            Dict with 'content', 'model', 'fallback_used' (bool), and potentially 'error'.
        """
        from tools.llm_client import call_ollama

        chain = self._get_chain(primary_model)
        last_error: Optional[str] = None

        for i, model in enumerate(chain):
            try:
                result = await call_ollama(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                if result.get("error"):
                    last_error = result["error"]
                    logger.warning(
                        "Model %s failed (attempt %d/%d): %s",
                        model, i + 1, len(chain), last_error,
                    )
                    continue

                content = result.get("content", "")
                if content.strip():
                    result["fallback_used"] = (i > 0)
                    if i > 0:
                        logger.info("Fallback succeeded with model: %s", model)
                    return result

                last_error = "Empty response"
                logger.warning("Model %s returned empty response", model)

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(
                    "Model %s raised exception (attempt %d/%d): %s",
                    model, i + 1, len(chain), last_error,
                )

        # All models failed
        return {
            "content": "",
            "model": chain[0] if chain else "unknown",
            "error": f"All models in fallback chain failed. Last error: {last_error}",
            "fallback_used": True,
            "done": True,
        }

    async def check_availability(self) -> Dict[str, bool]:
        """
        Check which models are currently available.

        Returns:
            Dict mapping model name to availability (True/False).
        """
        try:
            from tools.llm_client import list_models

            models = await list_models()
            if models and "error" in models[0]:
                logger.warning("Cannot check model availability: %s", models[0]["error"])
                return {}

            available_names = {m.get("name", "") for m in models}

            chain = self._get_chain()
            result: Dict[str, bool] = {}
            for model in chain:
                # Check if model name matches (allowing tag variations)
                base_name = model.split(":")[0]
                result[model] = any(
                    name.startswith(base_name) for name in available_names
                )

            return result

        except Exception as e:
            logger.error("Failed to check model availability: %s", e)
            return {}


model_fallback = ModelFallback()


async def get_fallback_response(
    messages: List[Dict[str, str]],
    primary_model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience async function for calling LLM with fallback.

    Args:
        messages: Chat messages.
        primary_model: Preferred model.

    Returns:
        LLM response dict.
    """
    return await model_fallback.call_with_fallback(messages, primary_model)
