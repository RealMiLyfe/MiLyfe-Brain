"""
Agent Pooling - Pre-warm instances for faster response.

Maintains a pool of pre-initialized agents ready for immediate task assignment.
Eliminates cold-start latency for common agent roles.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PooledAgent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = ""
    model: str = ""
    status: str = "idle"  # idle, busy, warming, retired
    current_task_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    tasks_completed: int = 0
    avg_response_ms: float = 0.0
    warm: bool = False  # Has the model been loaded/primed


class AgentPool:
    """Manages a pool of pre-warmed agent instances."""

    def __init__(self):
        self._pool: Dict[str, PooledAgent] = {}
        self._config = {
            "min_idle_per_role": 1,
            "max_per_role": 5,
            "max_total": 20,
            "idle_timeout_seconds": 600,
            "warmup_prompt": "You are ready. Acknowledge with 'ready'.",
        }
        self._role_config = {
            "orchestrator": {"min_idle": 1, "max": 3, "model": "hermes3:latest"},
            "coder": {"min_idle": 2, "max": 5, "model": "qwen2.5:14b"},
            "researcher": {"min_idle": 1, "max": 3, "model": "llama3.1:8b"},
            "executor": {"min_idle": 1, "max": 3, "model": "qwen2.5:14b"},
            "critic": {"min_idle": 1, "max": 2, "model": "qwen2.5:14b"},
            "debugger": {"min_idle": 1, "max": 2, "model": "qwen2.5:14b"},
        }

    async def initialize(self):
        """Pre-warm the minimum agents for each role."""
        for role, config in self._role_config.items():
            for _ in range(config["min_idle"]):
                await self._spawn_warm_agent(role, config["model"])

    async def _spawn_warm_agent(self, role: str, model: str) -> PooledAgent:
        """Create and warm up an agent."""
        agent = PooledAgent(role=role, model=model, status="warming")
        self._pool[agent.id] = agent
        # Simulate warmup (in production, would prime the model)
        agent.warm = True
        agent.status = "idle"
        return agent

    async def acquire(self, role: str, task_id: Optional[str] = None) -> Optional[PooledAgent]:
        """Acquire an idle agent from the pool."""
        # Find idle agent of requested role
        for agent in self._pool.values():
            if agent.role == role and agent.status == "idle" and agent.warm:
                agent.status = "busy"
                agent.current_task_id = task_id
                agent.last_active = time.time()
                return agent

        # No idle agent available - spawn new if within limits
        role_count = sum(1 for a in self._pool.values() if a.role == role)
        max_for_role = self._role_config.get(role, {}).get("max", 5)

        if role_count < max_for_role and len(self._pool) < self._config["max_total"]:
            model = self._role_config.get(role, {}).get("model", "llama3.1:8b")
            agent = await self._spawn_warm_agent(role, model)
            agent.status = "busy"
            agent.current_task_id = task_id
            return agent

        return None  # Pool exhausted

    async def release(self, agent_id: str, success: bool = True, duration_ms: float = 0):
        """Release an agent back to the pool."""
        agent = self._pool.get(agent_id)
        if not agent:
            return

        agent.status = "idle"
        agent.current_task_id = None
        agent.last_active = time.time()
        agent.tasks_completed += 1

        # Update rolling average response time
        n = agent.tasks_completed
        agent.avg_response_ms = ((agent.avg_response_ms * (n - 1)) + duration_ms) / n

    async def retire(self, agent_id: str):
        """Retire an agent from the pool."""
        agent = self._pool.get(agent_id)
        if agent:
            agent.status = "retired"
            del self._pool[agent_id]

    async def cleanup_idle(self):
        """Retire agents that have been idle too long."""
        now = time.time()
        timeout = self._config["idle_timeout_seconds"]
        to_retire = []

        for agent in self._pool.values():
            if agent.status == "idle" and (now - agent.last_active) > timeout:
                # Keep minimum per role
                idle_for_role = sum(
                    1 for a in self._pool.values()
                    if a.role == agent.role and a.status == "idle"
                )
                min_idle = self._role_config.get(agent.role, {}).get("min_idle", 1)
                if idle_for_role > min_idle:
                    to_retire.append(agent.id)

        for agent_id in to_retire:
            await self.retire(agent_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        by_role: Dict[str, Dict] = {}
        for agent in self._pool.values():
            if agent.role not in by_role:
                by_role[agent.role] = {"idle": 0, "busy": 0, "warming": 0, "total": 0}
            by_role[agent.role][agent.status] = by_role[agent.role].get(agent.status, 0) + 1
            by_role[agent.role]["total"] += 1

        return {
            "total_agents": len(self._pool),
            "by_role": by_role,
            "config": self._config,
        }


# Singleton
agent_pool = AgentPool()
