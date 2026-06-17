"""
Brain-to-Brain Communication - Inter-brain messaging protocol.

Enables multiple MiLyfe Brain instances to communicate, share knowledge,
delegate tasks, and synchronize state across a network of brains.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx


class MessageType(str, Enum):
    REQUEST = "request"          # Ask another brain to do something
    RESPONSE = "response"        # Reply to a request
    BROADCAST = "broadcast"      # Announce to all brains
    SYNC = "sync"               # Synchronize state/knowledge
    HEARTBEAT = "heartbeat"     # Keep-alive signal
    DELEGATE = "delegate"       # Delegate a task
    KNOWLEDGE = "knowledge"     # Share learned knowledge


@dataclass
class BrainNode:
    """A node in the brain network."""
    id: str
    name: str
    url: str
    capabilities: List[str] = field(default_factory=list)
    status: str = "online"
    last_heartbeat: float = field(default_factory=time.time)
    tasks_delegated: int = 0
    tasks_received: int = 0


@dataclass
class BrainMessage:
    """A message between brains."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_brain: str = ""
    target_brain: str = ""  # Empty for broadcast
    message_type: MessageType = MessageType.REQUEST
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None  # For request/response matching
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # Time to live in seconds


class BrainNetwork:
    """Manages the network of interconnected Brain instances."""

    def __init__(self):
        self.brain_id = f"brain-{uuid.uuid4().hex[:8]}"
        self.brain_name = "MiLyfe Brain"
        self._peers: Dict[str, BrainNode] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_log: List[BrainMessage] = []
        self._client = httpx.AsyncClient(timeout=30)

    async def register_peer(self, peer_id: str, name: str, url: str, capabilities: List[str] = None):
        """Register a peer brain in the network."""
        self._peers[peer_id] = BrainNode(
            id=peer_id,
            name=name,
            url=url,
            capabilities=capabilities or [],
        )

    async def unregister_peer(self, peer_id: str):
        """Remove a peer from the network."""
        self._peers.pop(peer_id, None)

    def on_message(self, message_type: MessageType):
        """Decorator to register a message handler."""
        def decorator(func: Callable):
            if message_type not in self._message_handlers:
                self._message_handlers[message_type] = []
            self._message_handlers[message_type].append(func)
            return func
        return decorator

    async def send(self, target_brain: str, message_type: MessageType, payload: Dict[str, Any], wait_response: bool = False) -> Optional[BrainMessage]:
        """Send a message to a specific brain."""
        msg = BrainMessage(
            source_brain=self.brain_id,
            target_brain=target_brain,
            message_type=message_type,
            payload=payload,
        )

        peer = self._peers.get(target_brain)
        if not peer:
            raise ValueError(f"Unknown peer: {target_brain}")

        self._message_log.append(msg)

        # Send via HTTP
        try:
            resp = await self._client.post(
                f"{peer.url}/api/brain/receive",
                json={
                    "id": msg.id,
                    "source": self.brain_id,
                    "type": message_type.value,
                    "payload": payload,
                    "correlation_id": msg.correlation_id,
                },
            )
            if resp.status_code == 200:
                peer.last_heartbeat = time.time()
                if wait_response:
                    # Wait for response with timeout
                    future = asyncio.get_event_loop().create_future()
                    self._pending_requests[msg.id] = future
                    try:
                        result = await asyncio.wait_for(future, timeout=msg.ttl)
                        return result
                    except asyncio.TimeoutError:
                        del self._pending_requests[msg.id]
                        return None
        except Exception:
            peer.status = "offline"
            return None

        return msg

    async def broadcast(self, message_type: MessageType, payload: Dict[str, Any]):
        """Broadcast a message to all peers."""
        tasks = []
        for peer_id in self._peers:
            tasks.append(self.send(peer_id, message_type, payload))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def delegate_task(self, task_description: str, required_capabilities: List[str] = None) -> Optional[str]:
        """Delegate a task to the most suitable peer."""
        # Find peer with matching capabilities
        best_peer = None
        for peer in self._peers.values():
            if peer.status != "online":
                continue
            if required_capabilities:
                if all(cap in peer.capabilities for cap in required_capabilities):
                    best_peer = peer
                    break
            else:
                best_peer = peer
                break

        if not best_peer:
            return None

        response = await self.send(
            best_peer.id,
            MessageType.DELEGATE,
            {"task": task_description, "capabilities": required_capabilities or []},
            wait_response=True,
        )

        if response:
            best_peer.tasks_delegated += 1
            return response.payload.get("task_id")
        return None

    async def share_knowledge(self, knowledge_type: str, data: Dict[str, Any]):
        """Share learned knowledge with all peers."""
        await self.broadcast(
            MessageType.KNOWLEDGE,
            {"type": knowledge_type, "data": data, "source": self.brain_name},
        )

    async def receive_message(self, raw_message: Dict[str, Any]):
        """Handle an incoming message from another brain."""
        msg = BrainMessage(
            id=raw_message.get("id", str(uuid.uuid4())),
            source_brain=raw_message.get("source", ""),
            target_brain=self.brain_id,
            message_type=MessageType(raw_message.get("type", "request")),
            payload=raw_message.get("payload", {}),
            correlation_id=raw_message.get("correlation_id"),
        )
        self._message_log.append(msg)

        # Check if this is a response to a pending request
        if msg.correlation_id and msg.correlation_id in self._pending_requests:
            self._pending_requests[msg.correlation_id].set_result(msg)
            del self._pending_requests[msg.correlation_id]
            return

        # Dispatch to handlers
        handlers = self._message_handlers.get(msg.message_type, [])
        for handler in handlers:
            await handler(msg)

    async def heartbeat_loop(self, interval: int = 30):
        """Send periodic heartbeats to all peers."""
        while True:
            await self.broadcast(MessageType.HEARTBEAT, {"brain_id": self.brain_id, "status": "online"})
            await asyncio.sleep(interval)

    def get_network_status(self) -> Dict[str, Any]:
        """Get current network status."""
        return {
            "brain_id": self.brain_id,
            "brain_name": self.brain_name,
            "peers": [
                {"id": p.id, "name": p.name, "status": p.status, "capabilities": p.capabilities}
                for p in self._peers.values()
            ],
            "total_messages": len(self._message_log),
            "pending_requests": len(self._pending_requests),
        }


# Singleton
brain_network = BrainNetwork()
