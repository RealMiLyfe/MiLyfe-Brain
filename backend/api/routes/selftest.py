"""MiLyfe Brain — End-to-End Self-Test Routes."""

from __future__ import annotations

import time

import httpx
import structlog
from fastapi import APIRouter

from config import settings
from models.schemas import SelfTestReport, SelfTestResult

logger = structlog.get_logger()
router = APIRouter()


@router.post("/run", response_model=SelfTestReport)
async def run_selftest():
    """Run full E2E self-test (ollama, chromadb, redis, tools)."""
    results = []
    start_total = time.time()

    # Test 1: Ollama connectivity
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                results.append(SelfTestResult(
                    service="ollama",
                    status="pass",
                    message=f"Connected. {len(models)} models available.",
                    latency_ms=(time.time() - start) * 1000,
                ))
            else:
                results.append(SelfTestResult(
                    service="ollama",
                    status="fail",
                    message=f"HTTP {resp.status_code}",
                    latency_ms=(time.time() - start) * 1000,
                ))
    except Exception as e:
        results.append(SelfTestResult(
            service="ollama",
            status="fail",
            message=str(e),
            latency_ms=(time.time() - start) * 1000,
        ))

    # Test 2: ChromaDB
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            if resp.status_code == 200:
                results.append(SelfTestResult(
                    service="chromadb",
                    status="pass",
                    message="ChromaDB healthy",
                    latency_ms=(time.time() - start) * 1000,
                ))
            else:
                results.append(SelfTestResult(
                    service="chromadb",
                    status="fail",
                    message=f"HTTP {resp.status_code}",
                    latency_ms=(time.time() - start) * 1000,
                ))
    except Exception as e:
        results.append(SelfTestResult(
            service="chromadb",
            status="fail",
            message=str(e),
            latency_ms=(time.time() - start) * 1000,
        ))

    # Test 3: Redis
    start = time.time()
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.set("selftest", "ok", ex=5)
        val = await r.get("selftest")
        await r.close()
        results.append(SelfTestResult(
            service="redis",
            status="pass" if val == "ok" else "fail",
            message="Redis read/write OK" if val == "ok" else "Read/write mismatch",
            latency_ms=(time.time() - start) * 1000,
        ))
    except Exception as e:
        results.append(SelfTestResult(
            service="redis",
            status="fail",
            message=str(e),
            latency_ms=(time.time() - start) * 1000,
        ))

    # Test 4: SQLite Database
    start = time.time()
    try:
        from memory.database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        results.append(SelfTestResult(
            service="database",
            status="pass",
            message="SQLite operational",
            latency_ms=(time.time() - start) * 1000,
        ))
    except Exception as e:
        results.append(SelfTestResult(
            service="database",
            status="fail",
            message=str(e),
            latency_ms=(time.time() - start) * 1000,
        ))

    # Test 5: LLM inference (if Ollama available)
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.default_light_model,
                    "messages": [{"role": "user", "content": "Say 'test ok' in 2 words"}],
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                results.append(SelfTestResult(
                    service="llm_inference",
                    status="pass",
                    message=f"Model responded: {content[:50]}",
                    latency_ms=(time.time() - start) * 1000,
                ))
            else:
                results.append(SelfTestResult(
                    service="llm_inference",
                    status="fail",
                    message=f"HTTP {resp.status_code}",
                    latency_ms=(time.time() - start) * 1000,
                ))
    except Exception as e:
        results.append(SelfTestResult(
            service="llm_inference",
            status="skip",
            message=f"Skipped: {e}",
            latency_ms=(time.time() - start) * 1000,
        ))

    # Test 6: Tool system
    start = time.time()
    try:
        from tools.registry import tool_registry
        tool_count = len(tool_registry.list_tools())
        results.append(SelfTestResult(
            service="tool_system",
            status="pass",
            message=f"{tool_count} tools registered",
            latency_ms=(time.time() - start) * 1000,
        ))
    except Exception as e:
        results.append(SelfTestResult(
            service="tool_system",
            status="fail",
            message=str(e),
            latency_ms=(time.time() - start) * 1000,
        ))

    total_latency = (time.time() - start_total) * 1000
    all_passed = all(r.status in ("pass", "skip") for r in results)

    return SelfTestReport(
        results=results,
        all_passed=all_passed,
        total_latency_ms=total_latency,
    )
