"""Action log search, filter, and export routes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import io
import csv

from models.schemas import ActionLog

router = APIRouter()


@router.get("/", response_model=list[ActionLog])
async def get_logs(
    playbook_id: str = None,
    agent_role: str = None,
    action_type: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """Search and filter action logs."""
    from memory.database import db

    query = "SELECT * FROM action_logs WHERE 1=1"
    params = []

    if playbook_id:
        query += " AND playbook_id = ?"
        params.append(playbook_id)
    if agent_role:
        query += " AND agent_role = ?"
        params.append(agent_role)
    if action_type:
        query += " AND action_type = ?"
        params.append(action_type)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await db.fetch_all(query, tuple(params))
    return [
        ActionLog(
            id=row["id"],
            playbook_id=row.get("playbook_id"),
            agent_id=row.get("agent_id"),
            agent_role=row.get("agent_role"),
            action_type=row["action_type"],
            description=row["description"],
            result=row.get("result"),
            timestamp=row["timestamp"],
        )
        for row in rows
    ]


@router.get("/export")
async def export_logs(format: str = "csv"):
    """Export logs as CSV."""
    from memory.database import db

    rows = await db.fetch_all("SELECT * FROM action_logs ORDER BY timestamp DESC")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "playbook_id", "agent_id", "agent_role", "action_type", "description", "result", "timestamp"])

    for row in rows:
        writer.writerow([
            row["id"], row.get("playbook_id"), row.get("agent_id"),
            row.get("agent_role"), row["action_type"], row["description"],
            row.get("result"), row["timestamp"],
        ])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=action_logs.csv"},
    )


@router.get("/stats")
async def get_log_stats():
    """Get log statistics."""
    from memory.database import db

    total = await db.fetch_one("SELECT COUNT(*) as count FROM action_logs")
    by_type = await db.fetch_all(
        "SELECT action_type, COUNT(*) as count FROM action_logs GROUP BY action_type"
    )
    by_role = await db.fetch_all(
        "SELECT agent_role, COUNT(*) as count FROM action_logs GROUP BY agent_role"
    )

    return {
        "total": total["count"] if total else 0,
        "by_type": {row["action_type"]: row["count"] for row in by_type},
        "by_role": {row["agent_role"]: row["count"] for row in by_role if row["agent_role"]},
    }
