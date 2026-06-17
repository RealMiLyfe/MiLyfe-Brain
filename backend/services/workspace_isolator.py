"""
Multi-user workspace isolation for MiLyfe Brain.

Each user gets their own isolated workspace directory, database context,
and agent state. Prevents cross-user data access.

Architecture:
    /workspace/
    ├── shared/           # Shared resources (read-only)
    ├── users/
    │   ├── {user_id}/    # Per-user workspace
    │   │   ├── files/    # User's file workspace
    │   │   ├── output/   # Agent-generated output
    │   │   └── .milyfe/  # User-specific config
    │   └── ...
    └── system/           # System files (admin only)
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .logging_config import get_logger

logger = get_logger("workspace_isolator")


@dataclass
class UserWorkspace:
    """Represents an isolated user workspace."""
    user_id: str
    root_path: Path
    files_path: Path
    output_path: Path
    config_path: Path
    max_storage_mb: int = 5120  # 5GB default per user

    @property
    def total_size_mb(self) -> float:
        """Calculate total workspace size in MB."""
        total = 0
        for f in self.root_path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)

    @property
    def is_over_quota(self) -> bool:
        """Check if workspace exceeds storage quota."""
        return self.total_size_mb > self.max_storage_mb


class WorkspaceIsolationService:
    """Manages per-user workspace isolation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.getenv("WORKSPACE_DIR", "/workspace"))
        self.users_dir = self.base_dir / "users"
        self.shared_dir = self.base_dir / "shared"
        self.system_dir = self.base_dir / "system"

        # Ensure base directories exist
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        self.system_dir.mkdir(parents=True, exist_ok=True)

    def get_workspace(self, user_id: str) -> UserWorkspace:
        """Get or create a user's isolated workspace."""
        user_root = self.users_dir / user_id
        workspace = UserWorkspace(
            user_id=user_id,
            root_path=user_root,
            files_path=user_root / "files",
            output_path=user_root / "output",
            config_path=user_root / ".milyfe",
        )

        # Create directories if they don't exist
        workspace.files_path.mkdir(parents=True, exist_ok=True)
        workspace.output_path.mkdir(parents=True, exist_ok=True)
        workspace.config_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Workspace accessed for user {user_id}", extra={"user_id": user_id})
        return workspace

    def validate_path(self, user_id: str, requested_path: str) -> Optional[Path]:
        """Validate that a path request stays within the user's workspace.

        Returns the resolved absolute path if valid, None if access denied.
        """
        workspace = self.get_workspace(user_id)
        resolved = (workspace.files_path / requested_path).resolve()

        # Check if resolved path is within user workspace or shared dir
        allowed_roots = [workspace.root_path, self.shared_dir]
        for root in allowed_roots:
            try:
                resolved.relative_to(root.resolve())
                return resolved
            except ValueError:
                continue

        logger.warning(
            f"Path traversal attempt by user {user_id}: {requested_path}",
            extra={"user_id": user_id, "requested_path": requested_path},
        )
        return None

    def cleanup_workspace(self, user_id: str):
        """Remove a user's workspace entirely."""
        workspace = self.get_workspace(user_id)
        if workspace.root_path.exists():
            shutil.rmtree(workspace.root_path)
            logger.info(f"Workspace cleaned for user {user_id}", extra={"user_id": user_id})

    def get_storage_usage(self, user_id: str) -> dict:
        """Get storage usage stats for a user."""
        workspace = self.get_workspace(user_id)
        return {
            "user_id": user_id,
            "total_mb": round(workspace.total_size_mb, 2),
            "quota_mb": workspace.max_storage_mb,
            "usage_percent": round((workspace.total_size_mb / workspace.max_storage_mb) * 100, 1),
            "over_quota": workspace.is_over_quota,
        }

    def list_users(self) -> list:
        """List all users with workspaces."""
        users = []
        if self.users_dir.exists():
            for user_dir in self.users_dir.iterdir():
                if user_dir.is_dir():
                    users.append(user_dir.name)
        return users

    def copy_shared_resource(self, resource_name: str, user_id: str, dest_name: Optional[str] = None):
        """Copy a shared resource into a user's workspace."""
        source = self.shared_dir / resource_name
        if not source.exists():
            raise FileNotFoundError(f"Shared resource not found: {resource_name}")

        workspace = self.get_workspace(user_id)
        dest = workspace.files_path / (dest_name or resource_name)

        if source.is_file():
            shutil.copy2(source, dest)
        elif source.is_dir():
            shutil.copytree(source, dest, dirs_exist_ok=True)

        logger.info(
            f"Copied shared resource '{resource_name}' to user {user_id}",
            extra={"user_id": user_id, "resource": resource_name},
        )


# Singleton instance
workspace_isolator = WorkspaceIsolationService()
