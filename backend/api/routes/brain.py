"""
MiLyfe Brain - Brain Route

Core brain orchestration: onboarding, analytics, marketplace, voice, reproducibility, compliance.
"""
from __future__ import annotations

import logging
import platform
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Onboarding Endpoints
# ============================================================


@router.get("/onboarding/status")
async def onboarding_status() -> Dict[str, Any]:
    """Check onboarding status: whether system is ready for use."""
    checks = {
        "database_ready": False,
        "ollama_available": False,
        "workspace_exists": False,
        "models_pulled": False,
        "first_run": True,
    }

    # Database
    try:
        from memory.database import async_session_factory

        checks["database_ready"] = async_session_factory is not None
    except Exception:
        pass

    # Ollama
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            checks["ollama_available"] = resp.status_code == 200
            if resp.status_code == 200:
                data = resp.json()
                checks["models_pulled"] = len(data.get("models", [])) > 0
    except Exception:
        pass

    # Workspace
    checks["workspace_exists"] = settings.workspace_path.exists()

    # First run check (if any playbooks exist)
    try:
        from memory.database import PlaybookRow, async_session_factory
        from sqlalchemy import func, select

        if async_session_factory is not None:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(func.count(PlaybookRow.id))
                )
                count = result.scalar() or 0
                checks["first_run"] = count == 0
    except Exception:
        pass

    all_ready = checks["database_ready"] and checks["ollama_available"]
    return {"ready": all_ready, "checks": checks}


@router.get("/onboarding/system-info")
async def system_info() -> Dict[str, Any]:
    """Get system diagnostic information."""
    disk = shutil.disk_usage("/")

    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": platform.os.cpu_count(),  # type: ignore[attr-defined]
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "disk_used_percent": round((disk.used / disk.total) * 100, 1),
        "ollama_url": settings.ollama_base_url,
        "chroma_url": settings.chroma_url,
        "workspace_dir": str(settings.workspace_path),
    }


@router.get("/onboarding/recommend-models")
async def recommend_models() -> Dict[str, Any]:
    """Recommend models based on available system resources."""
    available_models: List[Dict[str, str]] = []

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                for model in data.get("models", []):
                    available_models.append({
                        "name": model.get("name", ""),
                        "size": model.get("size", ""),
                        "modified": model.get("modified_at", ""),
                    })
    except Exception:
        pass

    # Recommendations based on what's available
    recommendations = {
        "light": settings.default_light_model,
        "heavy": settings.default_heavy_model,
        "premium": settings.premium_model,
    }

    return {
        "available_models": available_models,
        "recommendations": recommendations,
        "current_config": {
            "default_light_model": settings.default_light_model,
            "default_heavy_model": settings.default_heavy_model,
            "premium_model": settings.premium_model,
        },
    }


# ============================================================
# Analytics Endpoints
# ============================================================


@router.get("/analytics/overview")
async def analytics_overview(
    days: int = Query(default=7, ge=1, le=90),
) -> Dict[str, Any]:
    """Get analytics overview for the specified period."""
    try:
        from services.analytics import analytics_service

        return await analytics_service.get_overview(days=days)
    except ImportError:
        # Fallback if analytics service not available
        return {
            "period_days": days,
            "total_playbooks": 0,
            "completed_playbooks": 0,
            "failed_playbooks": 0,
            "total_tokens_used": 0,
            "active_agents": 0,
        }
    except Exception as e:
        logger.error("Analytics overview failed: %s", e)
        return {"error": str(e), "period_days": days}


@router.get("/analytics/agents")
async def analytics_agents() -> Dict[str, Any]:
    """Get agent performance analytics."""
    try:
        from services.analytics import analytics_service

        return await analytics_service.get_agent_performance()
    except ImportError:
        return {"agents": [], "total_tasks_completed": 0}
    except Exception as e:
        logger.error("Agent analytics failed: %s", e)
        return {"error": str(e)}


# ============================================================
# Marketplace Endpoints
# ============================================================


@router.get("/marketplace")
async def marketplace_index() -> Dict[str, Any]:
    """Get marketplace index of available skills and playbooks."""
    try:
        from services.marketplace import marketplace_service

        return await marketplace_service.get_index()
    except ImportError:
        return {
            "skills": [],
            "playbook_templates": [],
            "total_items": 0,
        }
    except Exception as e:
        logger.error("Marketplace index failed: %s", e)
        return {"error": str(e)}


@router.get("/marketplace/search")
async def marketplace_search(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Search the marketplace."""
    try:
        from services.marketplace import marketplace_service

        return await marketplace_service.search(query=q, category=category)
    except ImportError:
        return {"results": [], "query": q, "total": 0}
    except Exception as e:
        logger.error("Marketplace search failed: %s", e)
        return {"error": str(e), "query": q}


# ============================================================
# Voice Endpoints
# ============================================================


@router.post("/voice/stt")
async def speech_to_text(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Convert speech audio to text."""
    try:
        from services.voice_interface import voice_service

        audio_data = await file.read()
        result = await voice_service.transcribe(
            audio_data=audio_data,
            filename=file.filename or "audio.wav",
        )
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="Voice service not available")
    except Exception as e:
        logger.error("Speech-to-text failed: %s", e)
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")


@router.get("/voice/capabilities")
async def voice_capabilities() -> Dict[str, Any]:
    """Get voice capabilities (available models, supported formats)."""
    try:
        from services.voice_interface import voice_service

        return await voice_service.get_capabilities()
    except ImportError:
        return {
            "stt_available": False,
            "tts_available": False,
            "supported_formats": ["wav", "mp3", "ogg"],
            "message": "Voice service not configured",
        }


# ============================================================
# Reproducibility Endpoints
# ============================================================


@router.post("/reproducibility/export/{playbook_id}")
async def export_as_ci(playbook_id: str) -> Dict[str, Any]:
    """Export a playbook execution as a reproducible CI configuration."""
    try:
        from services.reproducibility import reproducibility_service

        return await reproducibility_service.export_as_ci(playbook_id)
    except ImportError:
        raise HTTPException(status_code=501, detail="Reproducibility service not available")
    except Exception as e:
        logger.error("CI export failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ============================================================
# Compliance Endpoints
# ============================================================


@router.post("/compliance/scan-pii")
async def scan_pii(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Scan a file for personally identifiable information (PII)."""
    try:
        from services.compliance import compliance_service

        content = await file.read()
        text = content.decode("utf-8", errors="replace")
        result = await compliance_service.scan_pii(text, filename=file.filename)
        return result
    except ImportError:
        raise HTTPException(status_code=501, detail="Compliance service not available")
    except Exception as e:
        logger.error("PII scan failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/compliance/licenses")
async def scan_licenses() -> Dict[str, Any]:
    """Scan workspace for license files and dependency licenses."""
    try:
        from services.compliance import compliance_service

        return await compliance_service.scan_licenses(str(settings.workspace_path))
    except ImportError:
        return {
            "licenses_found": [],
            "workspace": str(settings.workspace_path),
            "message": "Compliance service not available",
        }
    except Exception as e:
        logger.error("License scan failed: %s", e)
        return {"error": str(e)}
