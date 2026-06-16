"""Skill Library — Learn reusable patterns from successful playbooks."""

import uuid
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger()


class SkillLibrary:
    """Learn and store reusable skill patterns."""

    async def learn_from_playbook(self, playbook_id: str) -> Optional[str]:
        """Extract a reusable skill from a completed playbook."""
        from memory.database import db

        playbook = await db.fetch_one(
            "SELECT * FROM playbooks WHERE id = ? AND status = 'completed'", (playbook_id,)
        )
        if not playbook:
            return None

        steps = await db.fetch_all(
            "SELECT * FROM playbook_steps WHERE playbook_id = ? AND status = 'completed'",
            (playbook_id,),
        )
        if not steps:
            return None

        # Create skill from successful execution
        skill_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        steps_json = str([{"description": s["description"], "agent_role": s.get("agent_role")} for s in steps])

        await db.execute(
            """INSERT INTO skills (id, name, description, category, steps_json, source_playbook_id, success_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, playbook["title"][:100], playbook["description"][:500],
             "learned", steps_json, playbook_id, 1, now),
        )

        logger.info("Skill learned", skill_id=skill_id, from_playbook=playbook_id)
        return skill_id

    async def find_similar_skill(self, description: str) -> Optional[dict]:
        """Find a skill similar to the given description."""
        from memory.database import db

        # Simple keyword matching (could be vector search)
        skills = await db.fetch_all("SELECT * FROM skills ORDER BY success_count DESC LIMIT 20")
        for skill in skills:
            # Basic similarity check
            desc_words = set(description.lower().split())
            skill_words = set(skill["description"].lower().split())
            overlap = len(desc_words & skill_words)
            if overlap >= 3:
                return dict(skill)
        return None

    async def increment_success(self, skill_id: str) -> None:
        """Increment skill success count."""
        from memory.database import db
        await db.execute("UPDATE skills SET success_count = success_count + 1 WHERE id = ?", (skill_id,))


# Global instance
skill_library = SkillLibrary()
