"""MiLyfe Brain — Safety System.

Provides permission management, human-in-the-loop approvals,
command classification, audit logging, and workspace snapshots.
"""

from safety.approvals import ApprovalRequest, ApprovalService, approval_service
from safety.command_classifier import classify_command
from safety.logger import AuditLogger, audit_logger
from safety.permissions import PermissionLevel, PermissionService, permission_service
from safety.snapshots import SnapshotService, snapshot_service

__all__ = [
    "PermissionLevel",
    "PermissionService",
    "permission_service",
    "ApprovalRequest",
    "ApprovalService",
    "approval_service",
    "classify_command",
    "AuditLogger",
    "audit_logger",
    "SnapshotService",
    "snapshot_service",
]
