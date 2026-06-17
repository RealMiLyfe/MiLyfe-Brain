"""Add users and workspace isolation tables

Revision ID: 002_users
Revises: 001_initial
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_users"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-user support tables."""

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("preferences", sa.Text, nullable=True),  # JSON
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("settings", sa.Text, nullable=True),  # JSON
    )
    op.create_index("ix_workspaces_user_id", "workspaces", ["user_id"])

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("permissions", sa.Text, nullable=True),  # JSON
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("last_used", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # Add user_id to existing tables for multi-tenancy
    op.add_column("playbooks", sa.Column("user_id", sa.String(36), nullable=True))
    op.add_column("chat_messages", sa.Column("user_id", sa.String(36), nullable=True))
    op.add_column("notifications", sa.Column("user_id", sa.String(36), nullable=True))
    op.add_column("scheduled_jobs", sa.Column("user_id", sa.String(36), nullable=True))

    op.create_index("ix_playbooks_user_id", "playbooks", ["user_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])


def downgrade() -> None:
    """Remove multi-user support."""
    op.drop_index("ix_notifications_user_id", "notifications")
    op.drop_index("ix_chat_messages_user_id", "chat_messages")
    op.drop_index("ix_playbooks_user_id", "playbooks")

    op.drop_column("scheduled_jobs", "user_id")
    op.drop_column("notifications", "user_id")
    op.drop_column("chat_messages", "user_id")
    op.drop_column("playbooks", "user_id")

    op.drop_table("api_keys")
    op.drop_table("workspaces")
    op.drop_table("users")
