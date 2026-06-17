"""
MiLyfe Brain - Self-Test Route

Run connectivity tests for all services.
"""
from __future__ import annotations

import logging
import time
from typing import List

import httpx
from fastapi import APIRouter

from config import settings
from models.schemas import SelfTestReport, SelfTestResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/run", response_model=SelfTestReport)
async def run_selftest() -> SelfTestReport:
    """Run connectivity tests for Ollama, ChromaDB, Redis, Database, and Tools."""
    results: List[SelfTestResult] = []

    # Test Ollama
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            passed = resp.status_code == 200
            msg = f"Status {resp.status_code}" if not passed else "Connected"
    except Exception as e:
        passed = False
        msg = str(e)
    results.append(SelfTestResult(
        name="ollama",
        passed=passed,
        message=msg,
        duration_ms=(time.time() - start) * 1000,
    ))

    # Test ChromaDB
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            passed = resp.status_code == 200
            msg = f"Status {resp.status_code}" if not passed else "Connected"
    except Exception as e:
        passed = False
        msg = str(e)
    results.append(SelfTestResult(
        name="chromadb",
        passed=passed,
        message=msg,
        duration_ms=(time.time() - start) * 1000,
    ))

    # Test Redis
    start = time.time()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_timeout=3.0)
        await r.ping()
        await r.aclose()
        passed = True
        msg = "Connected"
    except Exception as e:
        passed = False
        msg = str(e)
    results.append(SelfTestResult(
        name="redis",
        passed=passed,
        message=msg,
        duration_ms=(time.time() - start) * 1000,
    ))

    # Test Database
    start = time.time()
    try:
        from memory.database import async_session_factory

        if async_session_factory is not None:
            async with async_session_factory() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
            passed = True
            msg = "Connected"
        else:
            passed = False
            msg = "Session factory not initialized"
    except Exception as e:
        passed = False
        msg = str(e)
    results.append(SelfTestResult(
        name="database",
        passed=passed,
        message=msg,
        duration_ms=(time.time() - start) * 1000,
    ))

    # Test Tools Registry
    start = time.time()
    try:
        from tools.registry import tool_registry

        tool_count = len(tool_registry.list_tools())
        passed = tool_count > 0
        msg = f"{tool_count} tools registered"
    except Exception as e:
        passed = False
        msg = str(e)
    results.append(SelfTestResult(
        name="tools",
        passed=passed,
        message=msg,
        duration_ms=(time.time() - start) * 1000,
    ))

    # Build report
    passed_count = sum(1 for r in results if r.passed)
    return SelfTestReport(
        passed=passed_count == len(results),
        total=len(results),
        passed_count=passed_count,
        failed_count=len(results) - passed_count,
        results=results,
    )
