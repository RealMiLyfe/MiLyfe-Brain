"""Task management routes."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/")
async def list_tasks(playbook_id: str = None, status: str = None):
    """List tasks, optionally filtered by playbook or status."""
    from memory.database import db

    query = "SELECT * FROM playbook_steps WHERE 1=1"
    params = []

    if playbook_id:
        query += " AND playbook_id = ?"
        params.append(playbook_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY rowid"
    rows = await db.fetch_all(query, tuple(params))
    return [dict(row) for row in rows]


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task details."""
    from memory.database import db

    row = await db.fetch_one("SELECT * FROM playbook_steps WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a pending task."""
    from memory.database import db

    row = await db.fetch_one("SELECT * FROM playbook_steps WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled in current state")

    await db.execute("UPDATE playbook_steps SET status = 'cancelled' WHERE id = ?", (task_id,))
    return {"message": "Task cancelled", "task_id": task_id}


@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    """Retry a failed task."""
    from memory.database import db

    row = await db.fetch_one("SELECT * FROM playbook_steps WHERE id = ?", (task_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] != "failed":
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

    await db.execute(
        "UPDATE playbook_steps SET status = 'pending', result = NULL WHERE id = ?", (task_id,)
    )
    return {"message": "Task queued for retry", "task_id": task_id}
