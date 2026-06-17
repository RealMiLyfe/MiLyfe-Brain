"""Skill Library — Learned reusable patterns from playbook executions.

Agents can learn from successfully completed playbooks and store
reusable skills for future reference.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from memory.database import (
    async_session_factory,
    PlaybookModel,
    PlaybookStepModel,
    SkillModel,
)

logger = logging.getLogger(__name__)


class SkillLibrary:
    """Manages learned skills extracted from successful playbook executions.

    Features:
    - Extract and store skills from completed playbooks
    - List all available skills
    - Retrieve relevant skills based on keyword matching
    """

    async def learn_from_playbook(self, playbook_id: str) -> Optional[dict]:
        """Extract a skill from a completed playbook.

        Only creates a skill if the playbook completed successfully
        and has enough steps to constitute a reusable pattern.

        Args:
            playbook_id: UUID of the completed playbook.

        Returns:
            The created skill dict, or None if not suitable.
        """
        async with async_session_factory() as db:
            # Load playbook
            result = await db.execute(
                select(PlaybookModel).where(PlaybookModel.id == playbook_id)
            )
            playbook = result.scalar_one_or_none()

            if playbook is None or playbook.status != "completed":
                return None

            # Load steps
            steps_result = await db.execute(
                select(PlaybookStepModel)
                .where(PlaybookStepModel.playbook_id == playbook_id)
                .order_by(PlaybookStepModel.order_index)
            )
            steps = steps_result.scalars().all()

            if len(steps) < 2:
                return None

            # Create skill
            skill_id = str(uuid.uuid4())
            steps_json = json.dumps([
                {
                    "description": s.description,
                    "agent_role": s.agent_role,
                    "order": s.order_index,
                }
                for s in steps
            ])

            skill = SkillModel(
                id=skill_id,
                name=playbook.title,
                description=playbook.description or playbook.title,
                category=self._infer_category(playbook.title, steps),
                steps_json=steps_json,
                source_playbook_id=playbook_id,
                success_count=1,
                created_at=datetime.utcnow(),
            )
            db.add(skill)
            await db.commit()

            logger.info("Learned skill: %s from playbook %s", playbook.title, playbook_id)

            return {
                "id": skill_id,
                "name": playbook.title,
                "description": playbook.description,
                "category": skill.category,
                "steps_count": len(steps),
            }

    async def list_skills(self) -> List[dict]:
        """List all stored skills.

        Returns:
            List of skill dictionaries.
        """
        async with async_session_factory() as db:
            result = await db.execute(
                select(SkillModel).order_by(SkillModel.created_at.desc())
            )
            rows = result.scalars().all()

        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "category": row.category,
                "success_count": row.success_count,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def get_relevant_skills(self, input_text: str) -> List[dict]:
        """Retrieve skills relevant to the given input text.

        Uses simple keyword matching against skill names and descriptions.

        Args:
            input_text: The task or query to match against.

        Returns:
            List of matching skill dicts, ranked by relevance.
        """
        all_skills = await self.list_skills()
        input_lower = input_text.lower()
        input_words = set(input_lower.split())

        scored: List[tuple] = []
        for skill in all_skills:
            name_lower = (skill.get("name") or "").lower()
            desc_lower = (skill.get("description") or "").lower()
            skill_words = set(name_lower.split() + desc_lower.split())

            # Score by word overlap
            overlap = len(input_words & skill_words)
            if overlap > 0:
                scored.append((overlap, skill))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:10]]

    def _infer_category(self, title: str, steps: list) -> str:
        """Infer a category for the skill based on title and steps."""
        title_lower = title.lower()
        if any(w in title_lower for w in ["test", "testing", "spec"]):
            return "testing"
        if any(w in title_lower for w in ["deploy", "release", "ship"]):
            return "deployment"
        if any(w in title_lower for w in ["refactor", "clean", "organize"]):
            return "refactoring"
        if any(w in title_lower for w in ["build", "create", "implement"]):
            return "development"
        if any(w in title_lower for w in ["research", "investigate", "analyze"]):
            return "research"
        return "general"


# Singleton
skill_library = SkillLibrary()
