"""Add integrations and distributed queue tables

Revision ID: 004_integrations
Revises: 003_replay
Create Date: 2025-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_integrations"
down_revision: Union[str, None] = "003_replay"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add integrations and queue tables."""

    # Integration connections (Jira, Linear, Slack, etc.)
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),  # jira, linear, slack, discord, github, calendar
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("config", sa.Text, nullable=False),  # Encrypted JSON
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_sync", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_integrations_provider", "integrations", ["provider"])
    op.create_index("ix_integrations_user_id", "integrations", ["user_id"])

    # Integration webhooks
    op.create_table(
        "integration_webhooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("integration_id", sa.String(36), sa.ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("processed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("received_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_integration_webhooks_processed", "integration_webhooks", ["processed"])

    # Distributed task queue
    op.create_table(
        "task_queue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text, nullable=False),  # JSON
        sa.Column("priority", sa.Integer, nullable=False, server_default="5"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_queue_status", "task_queue", ["status"])
    op.create_index("ix_task_queue_priority", "task_queue", ["priority"])
    op.create_index("ix_task_queue_scheduled", "task_queue", ["scheduled_at"])
    op.create_index("ix_task_queue_worker", "task_queue", ["worker_id"])

    # Agent pool
    op.create_table(
        "agent_pool",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_role", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),  # idle, busy, warming
        sa.Column("current_task_id", sa.String(36), nullable=True),
        sa.Column("last_active", sa.DateTime, nullable=True),
        sa.Column("tasks_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_response_ms", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_pool_role", "agent_pool", ["agent_role"])
    op.create_index("ix_agent_pool_status", "agent_pool", ["status"])

    # Brain-to-Brain messages
    op.create_table(
        "brain_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_brain_id", sa.String(100), nullable=False),
        sa.Column("target_brain_id", sa.String(100), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),  # request, response, broadcast, sync
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_brain_messages_target", "brain_messages", ["target_brain_id"])
    op.create_index("ix_brain_messages_status", "brain_messages", ["status"])

    # Dream mode sessions
    op.create_table(
        "dream_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("schedule_cron", sa.String(100), nullable=False),
        sa.Column("tasks", sa.Text, nullable=False),  # JSON array of tasks
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("results", sa.Text, nullable=True),  # JSON
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Remove integrations and queue tables."""
    op.drop_table("dream_sessions")
    op.drop_table("brain_messages")
    op.drop_table("agent_pool")
    op.drop_table("task_queue")
    op.drop_table("integration_webhooks")
    op.drop_table("integrations")
