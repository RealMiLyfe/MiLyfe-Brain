"""Add execution replay and time travel tables

Revision ID: 003_replay
Revises: 002_users
Create Date: 2025-02-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_replay"
down_revision: Union[str, None] = "002_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add execution replay support."""

    # Execution snapshots for time travel
    op.create_table(
        "execution_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playbook_id", sa.String(36), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(36), nullable=True),
        sa.Column("snapshot_type", sa.String(30), nullable=False),  # pre_execution, post_execution, checkpoint
        sa.Column("state_json", sa.Text, nullable=False),  # Full state at this point
        sa.Column("workspace_diff", sa.Text, nullable=True),  # Git diff of workspace
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.Text, nullable=True),  # JSON
    )
    op.create_index("ix_execution_snapshots_playbook_id", "execution_snapshots", ["playbook_id"])
    op.create_index("ix_execution_snapshots_timestamp", "execution_snapshots", ["timestamp"])

    # Execution events for replay
    op.create_table(
        "execution_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("playbook_id", sa.String(36), sa.ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=True),
        sa.Column("agent_role", sa.String(20), nullable=True),
        sa.Column("data", sa.Text, nullable=False),  # JSON
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("duration_ms", sa.Integer, nullable=True),
    )
    op.create_index("ix_execution_events_playbook_id", "execution_events", ["playbook_id"])
    op.create_index("ix_execution_events_sequence", "execution_events", ["playbook_id", "sequence_number"])

    # Prompt experiments for self-improving prompts
    op.create_table(
        "prompt_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt_name", sa.String(100), nullable=False),
        sa.Column("variant", sa.String(10), nullable=False),  # A, B, C...
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_quality_score", sa.Float, nullable=True),
        sa.Column("avg_tokens_used", sa.Float, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_experiments_name", "prompt_experiments", ["prompt_name"])

    # Few-shot examples for auto-generation
    op.create_table(
        "few_shot_examples",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("output_text", sa.Text, nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False),
        sa.Column("times_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_playbook_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_few_shot_examples_category", "few_shot_examples", ["category"])
    op.create_index("ix_few_shot_examples_quality", "few_shot_examples", ["quality_score"])


def downgrade() -> None:
    """Remove execution replay tables."""
    op.drop_table("few_shot_examples")
    op.drop_table("prompt_experiments")
    op.drop_table("execution_events")
    op.drop_table("execution_snapshots")
