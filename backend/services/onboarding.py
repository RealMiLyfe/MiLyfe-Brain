"""MiLyfe Brain — Onboarding / First-Run Experience.

Interactive tutorial, diagnostic wizard, model recommendation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class OnboardingService:
    """Guides new users through setup and first playbook."""

    async def get_status(self) -> Dict:
        """Check onboarding completion status."""
        checks = {
            "ollama_installed": await self._check_ollama(),
            "models_available": await self._check_models(),
            "workspace_ready": Path(settings.workspace_dir).exists(),
            "first_playbook_run": await self._has_run_playbook(),
            "database_ready": True,  # If we got here, DB works
        }
        completed = sum(1 for v in checks.values() if v)
        return {
            "completed": completed == len(checks),
            "progress": completed / len(checks),
            "checks": checks,
            "next_step": self._get_next_step(checks),
        }

    async def get_system_info(self) -> Dict:
        """Diagnostic wizard — system environment info."""
        import platform
        import shutil

        # RAM
        try:
            import os
            mem_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            ram_gb = mem_bytes / (1024**3)
        except Exception:
            ram_gb = 0

        # Disk
        disk = shutil.disk_usage("/")
        disk_free_gb = disk.free / (1024**3)

        # GPU (check for AMD ROCm or NVIDIA)
        gpu_info = await self._detect_gpu()

        return {
            "platform": platform.system(),
            "python": sys.version.split()[0],
            "ram_gb": round(ram_gb, 1),
            "disk_free_gb": round(disk_free_gb, 1),
            "cpu_count": os.cpu_count(),
            "gpu": gpu_info,
            "docker": shutil.which("docker") is not None,
        }

    async def recommend_models(self) -> List[Dict]:
        """Recommend models based on system resources."""
        info = await self.get_system_info()
        ram = info.get("ram_gb", 0)

        recommendations = []

        if ram >= 32:
            recommendations.append({
                "model": "llama3.1:70b",
                "role": "premium",
                "reason": "You have enough RAM for large models",
            })
        if ram >= 16:
            recommendations.append({
                "model": "qwen2.5:14b",
                "role": "heavy",
                "reason": "Great for coding tasks with 16GB+ RAM",
            })
            recommendations.append({
                "model": "llama3.1:8b",
                "role": "heavy",
                "reason": "Excellent general-purpose model",
            })
        if ram >= 8:
            recommendations.append({
                "model": "phi3:mini",
                "role": "light",
                "reason": "Fast and efficient for simple tasks",
            })

        if not recommendations:
            recommendations.append({
                "model": "phi3:mini",
                "role": "light",
                "reason": "Minimum requirement for MiLyfe Brain",
            })

        return recommendations

    def get_tutorial_steps(self) -> List[Dict]:
        """Get interactive tutorial steps."""
        return [
            {
                "step": 1,
                "title": "Welcome to MiLyfe Brain",
                "description": "Your 100% local AI agent swarm. No cloud. No API keys.",
                "action": None,
            },
            {
                "step": 2,
                "title": "Check System",
                "description": "Let's verify Ollama is running and models are available.",
                "action": "run_diagnostic",
            },
            {
                "step": 3,
                "title": "Your First Playbook",
                "description": "Try: 'Create a Python script that generates a random password'",
                "action": "create_playbook",
                "template": {
                    "title": "Generate Password Script",
                    "description": "Create a Python script that generates secure random passwords with configurable length and character types",
                },
            },
            {
                "step": 4,
                "title": "Watch the Swarm",
                "description": "Observe agents collaborating in real-time on the Dashboard.",
                "action": "view_dashboard",
            },
            {
                "step": 5,
                "title": "You're Ready!",
                "description": "Explore Chat, Schedule jobs, or create more complex playbooks.",
                "action": None,
            },
        ]

    async def _check_ollama(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def _check_models(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    return len(resp.json().get("models", [])) > 0
        except Exception:
            pass
        return False

    async def _has_run_playbook(self) -> bool:
        try:
            from memory.database import PlaybookRow, async_session_factory
            from sqlalchemy import select, func
            async with async_session_factory() as session:
                result = await session.execute(select(func.count(PlaybookRow.id)))
                return (result.scalar() or 0) > 0
        except Exception:
            return False

    async def _detect_gpu(self) -> Dict:
        import asyncio
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return {"type": "nvidia", "info": stdout.decode().strip()}
        except Exception:
            pass

        # Check AMD
        if Path("/dev/kfd").exists():
            return {"type": "amd_rocm", "info": "ROCm device detected"}

        return {"type": "none", "info": "No GPU detected (CPU-only mode)"}

    def _get_next_step(self, checks: Dict) -> str:
        if not checks["ollama_installed"]:
            return "Install and start Ollama: https://ollama.ai"
        if not checks["models_available"]:
            return "Pull a model: ollama pull phi3:mini"
        if not checks["first_playbook_run"]:
            return "Create your first playbook!"
        return "All set! Explore advanced features."


# Singleton
onboarding_service = OnboardingService()
