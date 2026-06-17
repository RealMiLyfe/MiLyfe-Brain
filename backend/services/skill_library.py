"""
MiLyfe Brain - Skill Library Service

Manages reusable skills learned from playbook executions.
Provides similarity search for matching skills to new tasks.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillLibrary:
    """
    Manages a library of learned skills.

    Skills are extracted from successful playbook executions and stored
    for reuse in similar future tasks.
    """

    def __init__(self) -> None:
        self._initialized: bool = False
        self._skills_cache: List[Dict[str, str]] = []

    async def initialize(self) -> None:
        """Load skills from database into cache."""
        try:
            from sqlalchemy import select

            from memory.database import SkillRow, async_session_factory

            if async_session_factory is None:
                self._initialized = True
                return

            async with async_session_factory() as session:
                result = await session.execute(
                    select(SkillRow).where(SkillRow.enabled == True)  # noqa: E712
                )
                rows = result.scalars().all()
                self._skills_cache = [
                    {
                        "id": row.id,
                        "name": row.name,
                        "description": row.description or "",
                        "trigger": row.trigger or "",
                        "agent_role": row.agent_role or "",
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to load skills: %s", e)

        self._initialized = True
        logger.info("SkillLibrary initialized (%d skills loaded)", len(self._skills_cache))

    async def find_similar_skills(self, query: str, limit: int = 3) -> List[str]:
        """
        Find skills similar to the given query using keyword matching.

        For production use, this could be backed by vector similarity search.

        Args:
            query: Task description or search query.
            limit: Maximum number of results to return.

        Returns:
            List of skill descriptions that match the query.
        """
        if not self._initialized:
            await self.initialize()

        if not self._skills_cache:
            return []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score each skill by keyword overlap
        scored: List[tuple] = []
        for skill in self._skills_cache:
            skill_text = f"{skill['name']} {skill['description']} {skill['trigger']}".lower()
            skill_words = set(skill_text.split())

            overlap = len(query_words & skill_words)
            if overlap > 0:
                scored.append((overlap, skill["description"] or skill["name"]))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [desc for _, desc in scored[:limit]]

    async def learn_from_playbook(self, playbook_id: str) -> Optional[str]:
        """
        Extract and store a skill from a completed playbook.

        Args:
            playbook_id: ID of the completed playbook.

        Returns:
            Skill ID if created, None otherwise.
        """
        from uuid import uuid4

        try:
            from sqlalchemy import select

            from memory.database import (
                PlaybookRow,
                PlaybookStepRow,
                SkillRow,
                async_session_factory,
            )

            if async_session_factory is None:
                return None

            # Load playbook and its steps
            async with async_session_factory() as session:
                pb_result = await session.execute(
                    select(PlaybookRow).where(PlaybookRow.id == playbook_id)
                )
                playbook = pb_result.scalar_one_or_none()
                if playbook is None or playbook.status != "completed":
                    return None

                steps_result = await session.execute(
                    select(PlaybookStepRow)
                    .where(PlaybookStepRow.playbook_id == playbook_id)
                    .order_by(PlaybookStepRow.order_num)
                )
                steps = steps_result.scalars().all()

            if not steps:
                return None

            # Build skill from playbook
            import json

            skill_id = str(uuid4())
            step_descriptions = [s.title for s in steps]

            skill = SkillRow(
                id=skill_id,
                name=playbook.title[:200],
                description=playbook.goal[:500],
                trigger=playbook.title.lower()[:500],
                steps=json.dumps(step_descriptions),
                agent_role=steps[0].agent_role if steps else None,
                tags=playbook.tags,
                enabled=True,
            )

            async with async_session_factory() as session:
                session.add(skill)
                await session.commit()

            # Update cache
            self._skills_cache.append({
                "id": skill_id,
                "name": playbook.title[:200],
                "description": playbook.goal[:500],
                "trigger": playbook.title.lower()[:500],
                "agent_role": steps[0].agent_role if steps else "",
            })

            logger.info("Learned new skill from playbook %s: %s", playbook_id, playbook.title)
            return skill_id

        except Exception as e:
            logger.error("Failed to learn from playbook %s: %s", playbook_id, e)
            return None


# Singleton instance
_skill_library: Optional[SkillLibrary] = None


def get_skill_library() -> SkillLibrary:
    """Factory function to get or create the SkillLibrary singleton."""
    global _skill_library
    if _skill_library is None:
        _skill_library = SkillLibrary()
    return _skill_library
