"""MiLyfe Brain — Agent Memory Sharing & Collaboration Protocol.

Shared memory space, agent negotiation, consensus, knowledge graph.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger()


class SharedMemory:
    """Shared memory space ('war room') for agent swarms."""

    def __init__(self):
        self._spaces: Dict[str, List[Dict]] = defaultdict(list)

    async def write(
        self,
        space_id: str,
        agent_id: str,
        agent_role: str,
        content: str,
        category: str = "note",
    ) -> str:
        """Write to shared memory space."""
        entry_id = str(uuid.uuid4())[:8]
        entry = {
            "id": entry_id,
            "agent_id": agent_id,
            "agent_role": agent_role,
            "content": content,
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._spaces[space_id].append(entry)
        return entry_id

    async def read(self, space_id: str, category: str = "") -> List[Dict]:
        """Read from shared memory space."""
        entries = self._spaces.get(space_id, [])
        if category:
            entries = [e for e in entries if e["category"] == category]
        return entries

    async def get_context_for_agent(self, space_id: str, agent_role: str) -> str:
        """Get formatted shared context for an agent."""
        entries = self._spaces.get(space_id, [])
        if not entries:
            return ""

        lines = ["[Shared Memory - War Room]"]
        for e in entries[-20:]:
            lines.append(f"[{e['agent_role']}] ({e['category']}): {e['content']}")
        return "\n".join(lines)


class ConsensusProtocol:
    """Voting/consensus when agents disagree."""

    async def propose(self, space_id: str, proposal: str, proposer: str) -> str:
        """Submit a proposal for voting."""
        prop_id = str(uuid.uuid4())[:8]
        self._proposals = getattr(self, '_proposals', {})
        self._proposals[prop_id] = {
            "id": prop_id,
            "proposal": proposal,
            "proposer": proposer,
            "votes": {},
            "status": "open",
        }
        return prop_id

    async def vote(self, proposal_id: str, voter: str, approve: bool, reason: str = "") -> Dict:
        """Cast a vote on a proposal."""
        self._proposals = getattr(self, '_proposals', {})
        prop = self._proposals.get(proposal_id)
        if not prop:
            return {"error": "Proposal not found"}

        prop["votes"][voter] = {"approve": approve, "reason": reason}

        # Check if consensus reached (majority)
        votes = prop["votes"]
        approvals = sum(1 for v in votes.values() if v["approve"])
        rejections = len(votes) - approvals

        if approvals > 2:
            prop["status"] = "approved"
        elif rejections > 2:
            prop["status"] = "rejected"

        return {"proposal_id": proposal_id, "status": prop["status"], "votes": len(votes)}

    async def get_result(self, proposal_id: str) -> Dict:
        """Get proposal result."""
        self._proposals = getattr(self, '_proposals', {})
        return self._proposals.get(proposal_id, {"error": "Not found"})


class KnowledgeGraph:
    """Simple knowledge graph for structured agent memories."""

    def __init__(self):
        self._nodes: Dict[str, Dict] = {}
        self._edges: List[Dict] = []

    async def add_node(self, node_id: str, label: str, type: str, data: Dict = None) -> str:
        """Add a knowledge node."""
        self._nodes[node_id] = {
            "id": node_id, "label": label, "type": type,
            "data": data or {}, "created": datetime.utcnow().isoformat(),
        }
        return node_id

    async def add_edge(self, source: str, target: str, relation: str) -> str:
        """Add a relationship between nodes."""
        edge_id = f"{source}->{target}"
        self._edges.append({
            "id": edge_id, "source": source, "target": target,
            "relation": relation,
        })
        return edge_id

    async def query(self, node_id: str = "", type: str = "") -> Dict:
        """Query the knowledge graph."""
        nodes = list(self._nodes.values())
        if node_id:
            nodes = [n for n in nodes if n["id"] == node_id]
        if type:
            nodes = [n for n in nodes if n["type"] == type]

        related_edges = [e for e in self._edges if any(n["id"] in (e["source"], e["target"]) for n in nodes)]
        return {"nodes": nodes, "edges": related_edges}


# Singletons
shared_memory = SharedMemory()
consensus_protocol = ConsensusProtocol()
knowledge_graph = KnowledgeGraph()
