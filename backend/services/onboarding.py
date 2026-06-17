"""
MiLyfe Brain - Onboarding Service

Provides system information, model recommendations, and guided
tutorial steps for new users.
"""
from __future__ import annotations

import logging
import platform
import shutil
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class OnboardingService:
    """Guides new users through system setup and configuration."""

    def __init__(self) -> None:
        pass

    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current onboarding status.

        Checks what has been configured and what still needs attention.

        Returns:
            Dict with completion status for each onboarding step.
        """
        from config import settings

        status = {
            "workspace_configured": False,
            "ollama_connected": False,
            "models_available": False,
            "first_playbook_run": False,
        }

        # Check workspace
        from pathlib import Path

        workspace = Path(settings.workspace_dir)
        status["workspace_configured"] = workspace.exists()

        # Check Ollama
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                status["ollama_connected"] = resp.status_code == 200
                data = resp.json()
                models = data.get("models", [])
                status["models_available"] = len(models) > 0
        except Exception:
            pass

        # Check if any playbooks have been run
        try:
            from sqlalchemy import func, select

            from memory.database import PlaybookRow, async_session_factory

            if async_session_factory is not None:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(func.count(PlaybookRow.id))
                    )
                    count = result.scalar() or 0
                    status["first_playbook_run"] = count > 0
        except Exception:
            pass

        return status

    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information for diagnostic purposes.

        Returns:
            Dict with OS, CPU, memory, GPU, and disk info.
        """
        info: Dict[str, Any] = {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_count": 0,
            "memory_total_gb": 0.0,
            "disk_free_gb": 0.0,
            "gpu_available": False,
        }

        try:
            import os
            info["cpu_count"] = os.cpu_count() or 0
        except Exception:
            pass

        try:
            import psutil
            mem = psutil.virtual_memory()
            info["memory_total_gb"] = round(mem.total / (1024 ** 3), 1)
        except ImportError:
            pass

        try:
            disk = shutil.disk_usage("/")
            info["disk_free_gb"] = round(disk.free / (1024 ** 3), 1)
        except Exception:
            pass

        # Check GPU (NVIDIA)
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                info["gpu_available"] = True
                info["gpu_name"] = result.stdout.strip().split("\n")[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return info

    async def recommend_models(self) -> List[Dict[str, Any]]:
        """
        Recommend LLM models based on system capabilities.

        Returns:
            List of model recommendation dicts with name, size, reason.
        """
        system_info = await self.get_system_info()
        memory_gb = system_info.get("memory_total_gb", 0.0)
        gpu_available = system_info.get("gpu_available", False)

        recommendations: List[Dict[str, Any]] = []

        if memory_gb >= 32 and gpu_available:
            recommendations.append({
                "name": "qwen2.5:14b",
                "role": "premium",
                "reason": "High-quality reasoning with your GPU — best for complex tasks.",
                "size_gb": 9.0,
            })
            recommendations.append({
                "name": "hermes3:latest",
                "role": "heavy",
                "reason": "Excellent general-purpose model for most tasks.",
                "size_gb": 4.7,
            })
        elif memory_gb >= 16:
            recommendations.append({
                "name": "hermes3:latest",
                "role": "heavy",
                "reason": "Good balance of quality and speed for 16GB+ systems.",
                "size_gb": 4.7,
            })
        else:
            recommendations.append({
                "name": "phi3:mini",
                "role": "heavy",
                "reason": "Lightweight but capable — fits in limited memory.",
                "size_gb": 2.3,
            })

        # Always recommend a light model
        recommendations.append({
            "name": "phi3:mini",
            "role": "light",
            "reason": "Fast responses for simple tasks and context summarization.",
            "size_gb": 2.3,
        })

        return recommendations

    def get_tutorial_steps(self) -> List[Dict[str, str]]:
        """
        Get the guided tutorial steps for new users.

        Returns:
            Ordered list of tutorial step dicts.
        """
        return [
            {
                "step": "1",
                "title": "Install Ollama",
                "description": "Download and install Ollama from https://ollama.ai",
                "command": "curl -fsSL https://ollama.ai/install.sh | sh",
            },
            {
                "step": "2",
                "title": "Pull a Model",
                "description": "Download at least one language model.",
                "command": "ollama pull phi3:mini",
            },
            {
                "step": "3",
                "title": "Verify Connection",
                "description": "Check that MiLyfe Brain can connect to Ollama.",
                "command": "curl http://localhost:11434/api/tags",
            },
            {
                "step": "4",
                "title": "Create Your First Playbook",
                "description": "Try creating a simple playbook to test the system.",
                "command": None,
            },
            {
                "step": "5",
                "title": "Explore the Dashboard",
                "description": "Visit the web UI to monitor playbooks, agents, and token usage.",
                "command": None,
            },
        ]


onboarding_service = OnboardingService()
