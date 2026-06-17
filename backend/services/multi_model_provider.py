"""
Multi-model cloud+local mixing for MiLyfe Brain (Phase 4).

Supports routing LLM calls to different providers based on:
- Model name prefix (ollama/, openai/, anthropic/, etc.)
- Task complexity (light → local, heavy → cloud)
- Fallback chain (try local first, fallback to cloud)
- Cost optimization (prefer local, use cloud for quality-critical)

Configuration:
    LLM_PROVIDERS=ollama,openai,anthropic
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    OPENAI_BASE_URL=https://api.openai.com/v1
    LLM_ROUTING_STRATEGY=local_first (local_first|cloud_first|cost_optimized|quality_first)
"""

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from .logging_config import get_logger

logger = get_logger("llm_provider")


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    GROQ = "groq"
    LOCAL = "local"  # Alias for Ollama


class RoutingStrategy(str, Enum):
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_FIRST = "quality_first"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: LLMProvider
    model_name: str
    display_name: str
    context_window: int = 4096
    cost_per_1k_input: float = 0.0  # USD
    cost_per_1k_output: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = False
    max_output_tokens: int = 4096
    quality_tier: str = "standard"  # standard, high, premium


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: LLMProvider
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0
    cost_usd: float = 0.0
    finish_reason: str = "stop"


# Model registry
AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    # Local (Ollama)
    "phi3:mini": ModelConfig(LLMProvider.OLLAMA, "phi3:mini", "Phi-3 Mini", 4096),
    "llama3.1:8b": ModelConfig(LLMProvider.OLLAMA, "llama3.1:8b", "LLaMA 3.1 8B", 131072),
    "qwen2.5:14b": ModelConfig(LLMProvider.OLLAMA, "qwen2.5:14b", "Qwen 2.5 14B", 32768),
    "hermes3:latest": ModelConfig(LLMProvider.OLLAMA, "hermes3:latest", "Hermes 3", 32768),
    # OpenAI
    "gpt-4o": ModelConfig(LLMProvider.OPENAI, "gpt-4o", "GPT-4o", 128000, 0.005, 0.015, True, True, 4096, "premium"),
    "gpt-4o-mini": ModelConfig(LLMProvider.OPENAI, "gpt-4o-mini", "GPT-4o Mini", 128000, 0.00015, 0.0006, True, True, 16384, "high"),
    # Anthropic
    "claude-3.5-sonnet": ModelConfig(LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", 200000, 0.003, 0.015, True, True, 8192, "premium"),
    "claude-3-haiku": ModelConfig(LLMProvider.ANTHROPIC, "claude-3-haiku-20240307", "Claude 3 Haiku", 200000, 0.00025, 0.00125, True, True, 4096, "standard"),
    # Groq (fast inference)
    "groq-llama3-70b": ModelConfig(LLMProvider.GROQ, "llama-3.1-70b-versatile", "LLaMA 3.1 70B (Groq)", 131072, 0.00059, 0.00079, True, True, 8000, "high"),
}


class MultiModelProvider:
    """Routes LLM calls to appropriate providers."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.strategy = RoutingStrategy(os.getenv("LLM_ROUTING_STRATEGY", "local_first"))
        self._client = httpx.AsyncClient(timeout=300)

    @property
    def available_providers(self) -> List[LLMProvider]:
        """List providers with valid credentials."""
        providers = [LLMProvider.OLLAMA]  # Always available locally
        if self.openai_key:
            providers.append(LLMProvider.OPENAI)
        if self.anthropic_key:
            providers.append(LLMProvider.ANTHROPIC)
        if self.groq_key:
            providers.append(LLMProvider.GROQ)
        return providers

    @property
    def available_models(self) -> List[Dict[str, Any]]:
        """List all available models based on configured providers."""
        models = []
        for name, config in AVAILABLE_MODELS.items():
            if config.provider in self.available_providers:
                models.append({
                    "id": name,
                    "name": config.display_name,
                    "provider": config.provider.value,
                    "context_window": config.context_window,
                    "quality_tier": config.quality_tier,
                    "cost_per_1k": config.cost_per_1k_input + config.cost_per_1k_output,
                })
        return models

    def select_model(self, requested_model: Optional[str] = None, complexity: str = "medium") -> ModelConfig:
        """Select the best model based on strategy and availability."""
        if requested_model and requested_model in AVAILABLE_MODELS:
            config = AVAILABLE_MODELS[requested_model]
            if config.provider in self.available_providers:
                return config

        # Strategy-based selection
        if self.strategy == RoutingStrategy.LOCAL_FIRST:
            return self._select_local_first(complexity)
        elif self.strategy == RoutingStrategy.QUALITY_FIRST:
            return self._select_quality_first(complexity)
        elif self.strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._select_cost_optimized(complexity)
        else:
            return self._select_local_first(complexity)

    def _select_local_first(self, complexity: str) -> ModelConfig:
        """Prefer local models, fallback to cloud."""
        if complexity == "light":
            return AVAILABLE_MODELS.get("phi3:mini", AVAILABLE_MODELS["llama3.1:8b"])
        elif complexity == "heavy":
            # Try local heavy model first
            if LLMProvider.OLLAMA in self.available_providers:
                return AVAILABLE_MODELS["qwen2.5:14b"]
            elif LLMProvider.OPENAI in self.available_providers:
                return AVAILABLE_MODELS["gpt-4o-mini"]
        return AVAILABLE_MODELS["llama3.1:8b"]

    def _select_quality_first(self, complexity: str) -> ModelConfig:
        """Prefer highest quality available."""
        if LLMProvider.ANTHROPIC in self.available_providers:
            return AVAILABLE_MODELS["claude-3.5-sonnet"]
        if LLMProvider.OPENAI in self.available_providers:
            return AVAILABLE_MODELS["gpt-4o"]
        return AVAILABLE_MODELS["qwen2.5:14b"]

    def _select_cost_optimized(self, complexity: str) -> ModelConfig:
        """Minimize cost (always prefer local)."""
        return AVAILABLE_MODELS.get("phi3:mini", AVAILABLE_MODELS["llama3.1:8b"])

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        complexity: str = "medium",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send a chat request to the appropriate provider."""
        config = self.select_model(model, complexity)
        start = time.time()

        try:
            if config.provider == LLMProvider.OLLAMA:
                response = await self._call_ollama(config, messages, temperature, max_tokens)
            elif config.provider == LLMProvider.OPENAI:
                response = await self._call_openai(config, messages, temperature, max_tokens)
            elif config.provider == LLMProvider.ANTHROPIC:
                response = await self._call_anthropic(config, messages, temperature, max_tokens)
            elif config.provider == LLMProvider.GROQ:
                response = await self._call_groq(config, messages, temperature, max_tokens)
            else:
                raise ValueError(f"Unknown provider: {config.provider}")

            response.duration_ms = (time.time() - start) * 1000
            response.cost_usd = (
                (response.prompt_tokens / 1000 * config.cost_per_1k_input) +
                (response.completion_tokens / 1000 * config.cost_per_1k_output)
            )

            logger.info(
                f"LLM call completed",
                extra={
                    "provider": config.provider.value,
                    "model": config.model_name,
                    "tokens": response.total_tokens,
                    "duration_ms": response.duration_ms,
                    "cost_usd": response.cost_usd,
                },
            )
            return response

        except Exception as e:
            logger.error(f"LLM call failed: {e}", extra={"provider": config.provider.value, "model": config.model_name})
            # Fallback to local if cloud fails
            if config.provider != LLMProvider.OLLAMA:
                logger.info("Falling back to local Ollama")
                fallback = AVAILABLE_MODELS["llama3.1:8b"]
                return await self._call_ollama(fallback, messages, temperature, max_tokens)
            raise

    async def _call_ollama(self, config: ModelConfig, messages: List[Dict], temperature: float, max_tokens: int) -> LLMResponse:
        """Call Ollama API."""
        resp = await self._client.post(
            f"{self.ollama_url}/api/chat",
            json={"model": config.model_name, "messages": messages, "stream": False,
                  "options": {"temperature": temperature, "num_predict": max_tokens}},
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=config.model_name,
            provider=LLMProvider.OLLAMA,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )

    async def _call_openai(self, config: ModelConfig, messages: List[Dict], temperature: float, max_tokens: int) -> LLMResponse:
        """Call OpenAI API."""
        resp = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_key}"},
            json={"model": config.model_name, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            model=config.model_name,
            provider=LLMProvider.OPENAI,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _call_anthropic(self, config: ModelConfig, messages: List[Dict], temperature: float, max_tokens: int) -> LLMResponse:
        """Call Anthropic API."""
        # Convert messages format for Anthropic
        system_msg = ""
        anthropic_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_msgs.append(msg)

        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01"},
            json={"model": config.model_name, "messages": anthropic_msgs,
                  "system": system_msg, "temperature": temperature, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return LLMResponse(
            content=data["content"][0]["text"],
            model=config.model_name,
            provider=LLMProvider.ANTHROPIC,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            finish_reason=data.get("stop_reason", "end_turn"),
        )

    async def _call_groq(self, config: ModelConfig, messages: List[Dict], temperature: float, max_tokens: int) -> LLMResponse:
        """Call Groq API (OpenAI-compatible)."""
        resp = await self._client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.groq_key}"},
            json={"model": config.model_name, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            model=config.model_name,
            provider=LLMProvider.GROQ,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton
llm_provider = MultiModelProvider()
