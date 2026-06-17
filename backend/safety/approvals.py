"""MiLyfe Brain — Human-in-the-Loop Approval System.

Provides async approval workflows for high-risk actions.
Uses asyncio.Event to allow callers to await user decisions.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    pending = "pending"
    approved = "approved"
    denied = "denied"
    expired = "expired"


@dataclass
class ApprovalRequest:
    """Represents a pending approval request for a high-risk action."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    description: str = ""
    details: Optional[str] = None
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    status: ApprovalStatus = ApprovalStatus.pending
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    @property
    def is_resolved(self) -> bool:
        """Whether this request has been approved or denied."""
        return self.status in (ApprovalStatus.approved, ApprovalStatus.denied, ApprovalStatus.expired)


class ApprovalService:
    """Manages approval requests for actions requiring human authorization.

    Agents await approval via asyncio.Event. The UI or API can approve/deny
    pending requests, which unblocks the waiting agent.
    """

    def __init__(self) -> None:
        self._requests: Dict[str, ApprovalRequest] = {}

    async def request_approval(
        self,
        action_type: str,
        description: str,
        details: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        timeout: float = 300.0,
    ) -> ApprovalRequest:
        """Create an approval request and wait for resolution.

        Args:
            action_type: Category of the action (e.g., 'file_delete').
            description: Human-readable description of what will happen.
            details: Optional additional context or parameters.
            agent_id: ID of the requesting agent.
            agent_role: Role of the requesting agent.
            timeout: Maximum seconds to wait for approval (default 5 minutes).

        Returns:
            The resolved ApprovalRequest (check .status for outcome).
        """
        request = ApprovalRequest(
            action_type=action_type,
            description=description,
            details=details,
            agent_id=agent_id,
            agent_role=agent_role,
        )
        self._requests[request.id] = request

        try:
            await asyncio.wait_for(request._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            request.status = ApprovalStatus.expired
            request.resolved_at = datetime.utcnow()

        return request

    def approve(self, request_id: str) -> bool:
        """Approve a pending request.

        Args:
            request_id: UUID of the approval request.

        Returns:
            True if the request was found and approved, False otherwise.
        """
        request = self._requests.get(request_id)
        if request is None or request.is_resolved:
            return False

        request.status = ApprovalStatus.approved
        request.resolved_at = datetime.utcnow()
        request._event.set()
        return True

    def deny(self, request_id: str) -> bool:
        """Deny a pending request.

        Args:
            request_id: UUID of the approval request.

        Returns:
            True if the request was found and denied, False otherwise.
        """
        request = self._requests.get(request_id)
        if request is None or request.is_resolved:
            return False

        request.status = ApprovalStatus.denied
        request.resolved_at = datetime.utcnow()
        request._event.set()
        return True

    def list_pending(self) -> List[ApprovalRequest]:
        """Return all pending (unresolved) approval requests.

        Returns:
            List of ApprovalRequest objects with status 'pending'.
        """
        return [r for r in self._requests.values() if r.status == ApprovalStatus.pending]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Retrieve a specific approval request by ID.

        Args:
            request_id: UUID of the request.

        Returns:
            The ApprovalRequest if found, None otherwise.
        """
        return self._requests.get(request_id)

    def clear_resolved(self) -> int:
        """Remove all resolved requests from memory.

        Returns:
            Number of requests cleared.
        """
        resolved_ids = [rid for rid, r in self._requests.items() if r.is_resolved]
        for rid in resolved_ids:
            del self._requests[rid]
        return len(resolved_ids)


# Singleton instance
approval_service = ApprovalService()
