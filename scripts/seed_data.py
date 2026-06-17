#!/usr/bin/env python3
"""
Seed database with development/testing data.

Usage:
    python scripts/seed_data.py              # Seed with default data
    python scripts/seed_data.py --clean      # Clear then seed
    python scripts/seed_data.py --minimal    # Minimal seed (just settings)
    python scripts/seed_data.py --production # Production-safe defaults only
"""

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Default database path
DB_PATH = Path("/data/milyfe.db")


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def generate_id() -> str:
    """Generate a UUID."""
    return str(uuid.uuid4())


def now() -> str:
    """Current timestamp."""
    return datetime.utcnow().isoformat()


def past(days: int = 0, hours: int = 0) -> str:
    """Past timestamp."""
    return (datetime.utcnow() - timedelta(days=days, hours=hours)).isoformat()


# ─── Seed Data ────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "default_light_model": "phi3:mini",
    "default_heavy_model": "llama3.1:8b",
    "premium_model": "llama3.1:70b",
    "max_agents": "10",
    "require_approval_destructive": "true",
    "require_approval_browsing": "true",
    "require_approval_gui": "true",
    "auto_git_snapshots": "true",
    "context_summarize_threshold": "32000",
    "max_retries": "3",
    "agent_timeout": "300",
    "output_style": "default",
    "theme": "dark",
    "notifications_enabled": "true",
    "daemon_enabled": "true",
    "workspace_dir": "/workspace",
}

EXAMPLE_PLAYBOOKS = [
    {
        "title": "Organize Project Files",
        "description": "Scan the workspace, identify file types, and reorganize into a clean directory structure with proper naming conventions.",
        "status": "completed",
    },
    {
        "title": "Build REST API",
        "description": "Create a FastAPI REST API with CRUD endpoints for a todo application, including models, routes, and error handling.",
        "status": "completed",
    },
    {
        "title": "Write Unit Tests",
        "description": "Analyze the existing codebase and generate comprehensive unit tests with pytest, targeting 80% coverage.",
        "status": "completed",
    },
    {
        "title": "Code Review",
        "description": "Review all Python files in the workspace for code quality, security issues, and performance improvements.",
        "status": "pending",
    },
    {
        "title": "Generate Documentation",
        "description": "Create API documentation, README updates, and inline code comments for the entire project.",
        "status": "pending",
    },
]

EXAMPLE_SKILLS = [
    {
        "name": "REST API Design",
        "description": "Create well-structured REST APIs with proper HTTP methods, status codes, and error handling.",
        "category": "api_design",
        "steps_json": json.dumps([
            "Identify resources and relationships",
            "Define endpoint URLs following REST conventions",
            "Implement request validation with Pydantic",
            "Add proper error responses",
            "Document with OpenAPI annotations",
        ]),
    },
    {
        "name": "Python Testing",
        "description": "Write comprehensive unit and integration tests using pytest.",
        "category": "testing",
        "steps_json": json.dumps([
            "Identify testable functions and classes",
            "Create test fixtures with conftest.py",
            "Write unit tests with assertions",
            "Add edge case and error tests",
            "Generate coverage report",
        ]),
    },
    {
        "name": "Docker Deployment",
        "description": "Containerize applications with Docker and Docker Compose.",
        "category": "docker",
        "steps_json": json.dumps([
            "Create multi-stage Dockerfile",
            "Define services in docker-compose.yml",
            "Configure environment variables",
            "Set up health checks",
            "Test with docker compose up",
        ]),
    },
    {
        "name": "Error Handling",
        "description": "Implement robust error handling with proper logging and user feedback.",
        "category": "error_handling",
        "steps_json": json.dumps([
            "Define custom exception classes",
            "Add try/except blocks at boundary layers",
            "Log errors with context",
            "Return user-friendly error messages",
            "Implement retry logic where appropriate",
        ]),
    },
    {
        "name": "Security Hardening",
        "description": "Review and harden application security.",
        "category": "security",
        "steps_json": json.dumps([
            "Validate all user inputs",
            "Implement authentication/authorization",
            "Sanitize file paths and shell commands",
            "Add rate limiting",
            "Review dependencies for vulnerabilities",
        ]),
    },
]

EXAMPLE_MEMORIES = [
    {"role": "coder", "memory_type": "preference", "content": "User prefers type hints on all functions", "importance": 0.8},
    {"role": "coder", "memory_type": "pattern", "content": "Project uses async/await pattern throughout", "importance": 0.9},
    {"role": "writer", "memory_type": "style", "content": "Documentation uses Google-style docstrings", "importance": 0.7},
    {"role": "orchestrator", "memory_type": "learning", "content": "Complex tasks benefit from parallel agent execution", "importance": 0.85},
    {"role": "critic", "memory_type": "standard", "content": "All code must pass ruff linting before acceptance", "importance": 0.95},
]

EXAMPLE_NOTIFICATIONS = [
    {"title": "Welcome to MiLyfe Brain!", "message": "Your AI agent swarm is ready. Try creating your first playbook.", "type": "info"},
    {"title": "System Ready", "message": "All services connected: Ollama, ChromaDB, Redis.", "type": "success"},
    {"title": "Tip: Quick Start", "message": "Use the Playbook tab to describe any task in plain English.", "type": "info"},
]


# ─── Seed Functions ───────────────────────────────────────────────────

def seed_settings(conn: sqlite3.Connection):
    """Seed default settings."""
    print("  Seeding settings...")
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now()),
        )
    conn.commit()
    print(f"    -> {len(DEFAULT_SETTINGS)} settings")


def seed_playbooks(conn: sqlite3.Connection):
    """Seed example playbooks."""
    print("  Seeding playbooks...")
    for i, pb in enumerate(EXAMPLE_PLAYBOOKS):
        pb_id = generate_id()
        created = past(days=len(EXAMPLE_PLAYBOOKS) - i)
        completed = created if pb["status"] == "completed" else None
        conn.execute(
            """INSERT INTO playbooks (id, title, description, status, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pb_id, pb["title"], pb["description"], pb["status"], created, completed),
        )

        # Add steps for completed playbooks
        if pb["status"] == "completed":
            roles = ["planner", "coder", "critic"]
            for j, role in enumerate(roles):
                conn.execute(
                    """INSERT INTO playbook_steps
                       (id, playbook_id, description, agent_role, status, order_index, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (generate_id(), pb_id, f"Step {j+1}: {role} task", role, "completed", j, created),
                )
    conn.commit()
    print(f"    -> {len(EXAMPLE_PLAYBOOKS)} playbooks")


def seed_skills(conn: sqlite3.Connection):
    """Seed learned skills."""
    print("  Seeding skills...")
    for skill in EXAMPLE_SKILLS:
        conn.execute(
            """INSERT INTO skills (id, name, description, category, steps_json, success_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), skill["name"], skill["description"],
             skill["category"], skill["steps_json"], 5, past(days=7)),
        )
    conn.commit()
    print(f"    -> {len(EXAMPLE_SKILLS)} skills")


def seed_memories(conn: sqlite3.Connection):
    """Seed agent memories."""
    print("  Seeding agent memories...")
    for mem in EXAMPLE_MEMORIES:
        conn.execute(
            """INSERT INTO agent_memories (id, role, memory_type, content, importance, recall_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (generate_id(), mem["role"], mem["memory_type"],
             mem["content"], mem["importance"], 3, past(days=5)),
        )
    conn.commit()
    print(f"    -> {len(EXAMPLE_MEMORIES)} memories")


def seed_notifications(conn: sqlite3.Connection):
    """Seed welcome notifications."""
    print("  Seeding notifications...")
    for notif in EXAMPLE_NOTIFICATIONS:
        conn.execute(
            """INSERT INTO notifications (id, title, message, type, read, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (generate_id(), notif["title"], notif["message"], notif["type"], 0, now()),
        )
    conn.commit()
    print(f"    -> {len(EXAMPLE_NOTIFICATIONS)} notifications")


def seed_token_usage(conn: sqlite3.Connection):
    """Seed sample token usage data for dashboard."""
    print("  Seeding token usage...")
    models = ["phi3:mini", "llama3.1:8b", "qwen2.5:14b"]
    roles = ["orchestrator", "coder", "researcher", "critic", "writer"]
    count = 0
    for day in range(7):
        for _ in range(10):
            conn.execute(
                """INSERT INTO token_usage
                   (id, agent_role, model, prompt_tokens, completion_tokens, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (generate_id(), roles[count % len(roles)], models[count % len(models)],
                 500 + (count * 37 % 2000), 200 + (count * 23 % 1000), past(days=day, hours=count % 24)),
            )
            count += 1
    conn.commit()
    print(f"    -> {count} token usage records")


def clean_database(conn: sqlite3.Connection):
    """Remove all data (keep schema)."""
    print("  Cleaning database...")
    tables = [
        "token_usage", "notifications", "scheduled_jobs", "settings",
        "skills", "agent_memories", "chat_messages", "action_logs",
        "playbook_steps", "playbooks",
    ]
    for table in tables:
        try:
            conn.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    print("    -> All tables cleared")


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed MiLyfe Brain database")
    parser.add_argument("--db", type=str, default=str(DB_PATH), help="Database path")
    parser.add_argument("--clean", action="store_true", help="Clear database before seeding")
    parser.add_argument("--minimal", action="store_true", help="Only seed settings")
    parser.add_argument("--production", action="store_true", help="Production-safe defaults only")
    args = parser.parse_args()

    db_path = args.db
    print(f"MiLyfe Brain Database Seeder")
    print(f"Database: {db_path}")
    print()

    # Check if DB exists
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        print("Run the application first to create tables, then seed.")
        sys.exit(1)

    conn = get_connection(db_path)

    try:
        if args.clean:
            clean_database(conn)
            print()

        if args.production:
            print("Seeding production defaults...")
            seed_settings(conn)
        elif args.minimal:
            print("Seeding minimal data...")
            seed_settings(conn)
            seed_notifications(conn)
        else:
            print("Seeding full development data...")
            seed_settings(conn)
            seed_playbooks(conn)
            seed_skills(conn)
            seed_memories(conn)
            seed_notifications(conn)
            seed_token_usage(conn)

        print()
        print("Seed complete!")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
