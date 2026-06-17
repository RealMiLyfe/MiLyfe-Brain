"""
MiLyfe Brain - Memory Sharing Service

Provides shared memory between agents and a simple consensus protocol
for multi-agent decision-making.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SharedMemory:
    """
    Thread-safe shared memory space for inter-agent communication.

    Agents can write and read named slots in shared memory.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def write(
        self,
        key: str,
        value: Any,
        agent_id: str,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        """
        Write a value to shared memory.

        Args:
            key: Memory slot key.
            value: Value to store.
            agent_id: ID of the writing agent.
            ttl_seconds: Optional time-to-live in seconds.
        """
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None

        self._store[key] = {
            "value": value,
            "agent_id": agent_id,
            "written_at": time.time(),
            "expires_at": expires_at,
        }

        logger.debug("SharedMemory: agent '%s' wrote key '%s'", agent_id, key)

    def read(self, key: str) -> Optional[Any]:
        """
        Read a value from shared memory.

        Args:
            key: Memory slot key.

        Returns:
            The stored value, or None if not found or expired.
        """
        entry = self._store.get(key)
        if entry is None:
            return None

        # Check expiration
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            del self._store[key]
            return None

        return entry["value"]

    def read_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Read value with metadata (who wrote it, when)."""
        entry = self._store.get(key)
        if entry is None:
            return None

        if entry["expires_at"] and time.time() > entry["expires_at"]:
            del self._store[key]
            return None

        return dict(entry)

    def list_keys(self) -> List[str]:
        """List all active (non-expired) keys."""
        self._cleanup_expired()
        return list(self._store.keys())

    def delete(self, key: str) -> bool:
        """Delete a key from shared memory."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [
            k for k, v in self._store.items()
            if v["expires_at"] and now > v["expires_at"]
        ]
        for k in expired:
            del self._store[k]


class ConsensusProtocol:
    """
    Simple consensus protocol for multi-agent decisions.

    Agents propose actions and vote; the proposal passes when a
    threshold of votes is reached.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        """
        Args:
            threshold: Fraction of votes needed to pass (0.0 - 1.0).
        """
        self._threshold = threshold
        self._proposals: Dict[str, Dict[str, Any]] = {}

    def propose(
        self,
        proposal_id: str,
        description: str,
        proposer_id: str,
        required_voters: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new proposal.

        Args:
            proposal_id: Unique proposal identifier.
            description: What is being proposed.
            proposer_id: ID of the proposing agent.
            required_voters: Optional list of agent IDs that must vote.

        Returns:
            Proposal status dict.
        """
        self._proposals[proposal_id] = {
            "id": proposal_id,
            "description": description,
            "proposer_id": proposer_id,
            "required_voters": required_voters or [],
            "votes": {},  # agent_id -> True/False
            "status": "pending",
            "created_at": time.time(),
        }

        logger.info("Proposal '%s' created by '%s': %s", proposal_id, proposer_id, description)
        return self._proposals[proposal_id]

    def vote(self, proposal_id: str, agent_id: str, approve: bool) -> Dict[str, Any]:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal to vote on.
            agent_id: Voting agent ID.
            approve: True to approve, False to reject.

        Returns:
            Updated proposal status.
        """
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return {"error": f"Proposal '{proposal_id}' not found"}

        if proposal["status"] != "pending":
            return {"error": f"Proposal '{proposal_id}' already resolved: {proposal['status']}"}

        proposal["votes"][agent_id] = approve

        # Check if consensus reached
        required = proposal["required_voters"]
        if required:
            all_voted = all(voter in proposal["votes"] for voter in required)
            if all_voted:
                approvals = sum(1 for v in proposal["votes"].values() if v)
                total = len(proposal["votes"])
                if approvals / total >= self._threshold:
                    proposal["status"] = "approved"
                else:
                    proposal["status"] = "rejected"
        else:
            # Simple threshold check against current votes
            if len(proposal["votes"]) >= 2:
                approvals = sum(1 for v in proposal["votes"].values() if v)
                total = len(proposal["votes"])
                if approvals / total >= self._threshold:
                    proposal["status"] = "approved"

        logger.debug(
            "Vote on '%s' by '%s': %s (status: %s)",
            proposal_id, agent_id, "approve" if approve else "reject", proposal["status"],
        )
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get a proposal's current status."""
        return self._proposals.get(proposal_id)

    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending proposals."""
        return [p for p in self._proposals.values() if p["status"] == "pending"]


# Singleton instances
shared_memory = SharedMemory()
consensus_protocol = ConsensusProtocol()
