"""MiLyfe Brain — Skill Library (Learn reusable patterns from success)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

import orjson
import structlog
from sqlalchemy import select

logger = structlog.get_logger()


class SkillLibrary:
    """Learns and stores reusable patterns from successful playbooks."""

    async def learn_from_playbook(self, playbook_id: str):
        """Extract a reusable skill from a completed playbook."""
        from memory.database import (
            PlaybookRow, PlaybookStepRow, SkillRow,
            async_session_factory,
        )

        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if not pb or pb.status != "completed":
                return None

            steps_result = await session.execute(
                select(PlaybookStepRow)
                .where(PlaybookStepRow.playbook_id == playbook_id)
                .order_by(PlaybookStepRow.order_index)
            )
            steps = steps_result.scalars().all()

            if len(steps) < 2:
                return None

            # Create skill
            skill_id = str(uuid.uuid4())
            steps_data = [
                {
                    "description": s.description,
                    "agent_role": s.agent_role,
                    "complexity": s.complexity,
                }
                for s in steps
            ]

            skill = SkillRow(
                id=skill_id,
                name=pb.title[:200],
                description=pb.description[:500],
                category=self._infer_category(pb.title, pb.description),
                steps_json=orjson.dumps(steps_data).decode(),
                source_playbook_id=playbook_id,
                success_count=1,
                triggers=orjson.dumps(self._extract_triggers(pb.title)).decode(),
                created_at=datetime.utcnow(),
            )
            session.add(skill)
            await session.commit()

            logger.info("skill_learned", skill_id=skill_id, name=pb.title[:50])
            return skill_id

    async def find_similar_skills(self, query: str, limit: int = 5) -> List[Dict]:
        """Find skills relevant to a query."""
        from memory.database import SkillRow, async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                select(SkillRow).order_by(SkillRow.success_count.desc()).limit(limit * 3)
            )
            skills = result.scalars().all()

        # Simple keyword matching (vector search would be better)
        query_words = set(query.lower().split())
        scored = []
        for skill in skills:
            triggers = orjson.loads(skill.triggers) if skill.triggers else []
            skill_words = set(skill.name.lower().split() + triggers)
            overlap = len(query_words & skill_words)
            if overlap > 0:
                scored.append((overlap, skill))

        scored.sort(key=lambda x: -x[0])
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "success_count": s.success_count,
            }
            for _, s in scored[:limit]
        ]

    async def increment_success(self, skill_id: str):
        """Increment success count for a skill."""
        from memory.database import SkillRow, async_session_factory

        async with async_session_factory() as session:
            skill = await session.get(SkillRow, skill_id)
            if skill:
                skill.success_count += 1
                await session.commit()

    def _infer_category(self, title: str, desc: str) -> str:
        combined = (title + " " + desc).lower()
        if any(w in combined for w in ["api", "endpoint", "rest", "graphql"]):
            return "api_design"
        if any(w in combined for w in ["test", "pytest", "jest", "spec"]):
            return "testing"
        if any(w in combined for w in ["deploy", "docker", "ci", "cd"]):
            return "devops"
        if any(w in combined for w in ["ui", "frontend", "react", "css"]):
            return "frontend"
        if any(w in combined for w in ["database", "sql", "migration"]):
            return "database"
        return "general"

    def _extract_triggers(self, title: str) -> List[str]:
        """Extract keyword triggers from title."""
        stop_words = {"a", "an", "the", "is", "are", "and", "or", "to", "for", "in", "on", "with"}
        words = [w.lower() for w in title.split() if w.lower() not in stop_words and len(w) > 2]
        return words[:10]


# Singleton
skill_library = SkillLibrary()
