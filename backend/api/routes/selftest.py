"""End-to-end self-test runner."""

import time

import httpx
from fastapi import APIRouter

from config import settings
from models.schemas import SelfTestResponse, SelfTestResult

router = APIRouter()


@router.post("/run", response_model=SelfTestResponse)
async def run_selftest():
    """Run full E2E self-test (ollama, chromadb, redis, tools)."""
    tests: list[SelfTestResult] = []
    start = time.time()

    # Test 1: Ollama connectivity
    t1_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                tests.append(SelfTestResult(
                    test_name="ollama_connection",
                    passed=True,
                    message=f"Connected. {len(models)} models available.",
                    duration_ms=(time.time() - t1_start) * 1000,
                ))
            else:
                tests.append(SelfTestResult(
                    test_name="ollama_connection",
                    passed=False,
                    message=f"HTTP {resp.status_code}",
                    duration_ms=(time.time() - t1_start) * 1000,
                ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="ollama_connection", passed=False,
            message=str(e), duration_ms=(time.time() - t1_start) * 1000,
        ))

    # Test 2: ChromaDB connectivity
    t2_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
            tests.append(SelfTestResult(
                test_name="chromadb_connection",
                passed=resp.status_code == 200,
                message="Connected" if resp.status_code == 200 else f"HTTP {resp.status_code}",
                duration_ms=(time.time() - t2_start) * 1000,
            ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="chromadb_connection", passed=False,
            message=str(e), duration_ms=(time.time() - t2_start) * 1000,
        ))

    # Test 3: Redis connectivity
    t3_start = time.time()
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        tests.append(SelfTestResult(
            test_name="redis_connection", passed=True,
            message="Connected", duration_ms=(time.time() - t3_start) * 1000,
        ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="redis_connection", passed=False,
            message=str(e), duration_ms=(time.time() - t3_start) * 1000,
        ))

    # Test 4: Database
    t4_start = time.time()
    try:
        from memory.database import db
        rows = await db.fetch_all("SELECT COUNT(*) as count FROM playbooks")
        tests.append(SelfTestResult(
            test_name="database", passed=True,
            message=f"Connected. {rows[0]['count']} playbooks.",
            duration_ms=(time.time() - t4_start) * 1000,
        ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="database", passed=False,
            message=str(e), duration_ms=(time.time() - t4_start) * 1000,
        ))

    # Test 5: Tool registry
    t5_start = time.time()
    try:
        from tools.registry import tool_registry
        tool_count = len(tool_registry.list_tools())
        tests.append(SelfTestResult(
            test_name="tool_registry", passed=tool_count > 0,
            message=f"{tool_count} tools registered",
            duration_ms=(time.time() - t5_start) * 1000,
        ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="tool_registry", passed=False,
            message=str(e), duration_ms=(time.time() - t5_start) * 1000,
        ))

    # Test 6: LLM inference (if Ollama available)
    t6_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.default_light_model,
                    "messages": [{"role": "user", "content": "Say 'test ok' and nothing else."}],
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                content = resp.json().get("message", {}).get("content", "")
                tests.append(SelfTestResult(
                    test_name="llm_inference", passed=True,
                    message=f"Response: {content[:50]}",
                    duration_ms=(time.time() - t6_start) * 1000,
                ))
            else:
                tests.append(SelfTestResult(
                    test_name="llm_inference", passed=False,
                    message=f"HTTP {resp.status_code}",
                    duration_ms=(time.time() - t6_start) * 1000,
                ))
    except Exception as e:
        tests.append(SelfTestResult(
            test_name="llm_inference", passed=False,
            message=str(e), duration_ms=(time.time() - t6_start) * 1000,
        ))

    total_duration = (time.time() - start) * 1000
    overall = all(t.passed for t in tests)

    return SelfTestResponse(overall=overall, tests=tests, duration_ms=total_duration)
