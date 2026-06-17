"""Initial schema - all core tables

Revision ID: 001_initial
Revises: None
Create Date: 2024-12-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""

    # Playbooks
    op.create_table(
        "playbooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_playbooks_status", "playbooks", ["status"])
    op.create_index("ix_playbooks_created_at", "playbooks", ["created_at"])

    # Playbook Steps
    op.create_table(
        "playbook_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playbook_id", sa.String(36), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("agent_role", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("depends_on", sa.Text, nullable=True),  # JSON array
        sa.Column("complexity", sa.String(10), nullable=True, server_default="medium"),
    )
    op.create_index("ix_playbook_steps_playbook_id", "playbook_steps", ["playbook_id"])

    # Action Logs
    op.create_table(
        "action_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playbook_id", sa.String(36), sa.ForeignKey("playbooks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("agent_role", sa.String(20), nullable=True),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_action_logs_timestamp", "action_logs", ["timestamp"])
    op.create_index("ix_action_logs_agent_role", "action_logs", ["agent_role"])
    op.create_index("ix_action_logs_action_type", "action_logs", ["action_type"])
    op.create_index("ix_action_logs_playbook_id", "action_logs", ["playbook_id"])

    # Chat Messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True, server_default="0"),
        sa.Column("tool_calls", sa.Text, nullable=True),  # JSON
        sa.Column("attachments", sa.Text, nullable=True),  # JSON
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    # Agent Memories
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("memory_type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("importance", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("recall_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_memories_role", "agent_memories", ["role"])

    # Skills
    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("steps_json", sa.Text, nullable=False),
        sa.Column("source_playbook_id", sa.String(36), nullable=True),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Settings
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Scheduled Jobs
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playbook_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("last_run", sa.DateTime, nullable=True),
        sa.Column("next_run", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("type", sa.String(30), nullable=False, server_default="info"),
        sa.Column("read", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_read", "notifications", ["read"])

    # Token Usage
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("agent_role", sa.String(20), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("playbook_id", sa.String(36), nullable=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_token_usage_timestamp", "token_usage", ["timestamp"])
    op.create_index("ix_token_usage_model", "token_usage", ["model"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("token_usage")
    op.drop_table("notifications")
    op.drop_table("scheduled_jobs")
    op.drop_table("settings")
    op.drop_table("skills")
    op.drop_table("agent_memories")
    op.drop_table("chat_messages")
    op.drop_table("action_logs")
    op.drop_table("playbook_steps")
    op.drop_table("playbooks")
