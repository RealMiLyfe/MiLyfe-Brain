"""
Execution Replay / Time Travel - Timeline scrubber and undo.

Records every agent action, tool call, and state change during playbook
execution. Allows users to replay, rewind, and branch from any point.

Features:
- Full execution recording (events + state snapshots)
- Timeline visualization data
- Rewind to any checkpoint
- Branch from past state (fork)
- Undo last N agent actions
- Diff between checkpoints
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(str, Enum):
    AGENT_SPAWNED = "agent_spawned"
    AGENT_THOUGHT = "agent_thought"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    CHECKPOINT = "checkpoint"
    USER_INTERVENTION = "user_intervention"


@dataclass
class ExecutionEvent:
    """A single event in the execution timeline."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    playbook_id: str = ""
    event_type: EventType = EventType.CHECKPOINT
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0
    timestamp: float = field(default_factory=time.time)
    duration_ms: Optional[float] = None
    reversible: bool = True
    undo_data: Optional[Dict] = None  # Data needed to reverse this event


@dataclass
class Checkpoint:
    """A saved state snapshot for time travel."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    playbook_id: str = ""
    sequence_number: int = 0
    label: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    workspace_snapshot: Optional[str] = None  # Git commit hash
    timestamp: float = field(default_factory=time.time)


@dataclass
class TimelineEntry:
    """Entry for timeline visualization."""
    id: str
    event_type: str
    label: str
    agent_role: Optional[str]
    timestamp: float
    duration_ms: float
    is_checkpoint: bool
    can_undo: bool
    details: Dict[str, Any]


class ExecutionReplayService:
    """Manages execution recording and replay."""

    def __init__(self):
        self._recordings: Dict[str, List[ExecutionEvent]] = {}
        self._checkpoints: Dict[str, List[Checkpoint]] = {}
        self._sequence_counters: Dict[str, int] = {}

    def start_recording(self, playbook_id: str):
        """Start recording execution for a playbook."""
        self._recordings[playbook_id] = []
        self._checkpoints[playbook_id] = []
        self._sequence_counters[playbook_id] = 0
        # Auto-create initial checkpoint
        self.create_checkpoint(playbook_id, "Initial state")

    def record_event(
        self,
        playbook_id: str,
        event_type: EventType,
        data: Dict[str, Any],
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        duration_ms: Optional[float] = None,
        undo_data: Optional[Dict] = None,
    ) -> ExecutionEvent:
        """Record an execution event."""
        if playbook_id not in self._recordings:
            self.start_recording(playbook_id)

        seq = self._sequence_counters.get(playbook_id, 0)
        self._sequence_counters[playbook_id] = seq + 1

        event = ExecutionEvent(
            playbook_id=playbook_id,
            event_type=event_type,
            agent_id=agent_id,
            agent_role=agent_role,
            data=data,
            sequence_number=seq,
            duration_ms=duration_ms,
            undo_data=undo_data,
            reversible=undo_data is not None,
        )
        self._recordings[playbook_id].append(event)
        return event

    def create_checkpoint(self, playbook_id: str, label: str, state: Optional[Dict] = None) -> Checkpoint:
        """Create a checkpoint for time travel."""
        seq = self._sequence_counters.get(playbook_id, 0)
        checkpoint = Checkpoint(
            playbook_id=playbook_id,
            sequence_number=seq,
            label=label,
            state=state or {},
        )
        if playbook_id not in self._checkpoints:
            self._checkpoints[playbook_id] = []
        self._checkpoints[playbook_id].append(checkpoint)
        return checkpoint

    def get_timeline(self, playbook_id: str) -> List[TimelineEntry]:
        """Get timeline data for visualization."""
        events = self._recordings.get(playbook_id, [])
        checkpoints = {c.sequence_number for c in self._checkpoints.get(playbook_id, [])}

        timeline = []
        for event in events:
            timeline.append(TimelineEntry(
                id=event.id,
                event_type=event.event_type.value,
                label=self._event_label(event),
                agent_role=event.agent_role,
                timestamp=event.timestamp,
                duration_ms=event.duration_ms or 0,
                is_checkpoint=event.sequence_number in checkpoints,
                can_undo=event.reversible,
                details=event.data,
            ))
        return timeline

    def undo_last(self, playbook_id: str, count: int = 1) -> List[ExecutionEvent]:
        """Undo the last N reversible events."""
        events = self._recordings.get(playbook_id, [])
        undone = []

        for _ in range(count):
            # Find last reversible event
            for i in range(len(events) - 1, -1, -1):
                if events[i].reversible and events[i] not in undone:
                    undone.append(events[i])
                    break

        return undone

    def rewind_to_checkpoint(self, playbook_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        """Rewind execution to a specific checkpoint."""
        checkpoints = self._checkpoints.get(playbook_id, [])
        for cp in checkpoints:
            if cp.id == checkpoint_id:
                # Remove all events after this checkpoint
                self._recordings[playbook_id] = [
                    e for e in self._recordings.get(playbook_id, [])
                    if e.sequence_number <= cp.sequence_number
                ]
                self._sequence_counters[playbook_id] = cp.sequence_number + 1
                return cp
        return None

    def fork_from_checkpoint(self, playbook_id: str, checkpoint_id: str) -> Optional[str]:
        """Create a new branch from a checkpoint."""
        checkpoints = self._checkpoints.get(playbook_id, [])
        for cp in checkpoints:
            if cp.id == checkpoint_id:
                # Create new playbook branch
                new_id = f"{playbook_id}__fork__{uuid.uuid4().hex[:8]}"
                events_to_copy = [
                    e for e in self._recordings.get(playbook_id, [])
                    if e.sequence_number <= cp.sequence_number
                ]
                self._recordings[new_id] = events_to_copy
                self._checkpoints[new_id] = [cp]
                self._sequence_counters[new_id] = cp.sequence_number + 1
                return new_id
        return None

    def get_diff(self, playbook_id: str, from_seq: int, to_seq: int) -> List[ExecutionEvent]:
        """Get events between two sequence numbers."""
        events = self._recordings.get(playbook_id, [])
        return [e for e in events if from_seq <= e.sequence_number <= to_seq]

    def _event_label(self, event: ExecutionEvent) -> str:
        """Generate human-readable label for an event."""
        labels = {
            EventType.AGENT_SPAWNED: f"Spawned {event.agent_role} agent",
            EventType.AGENT_THOUGHT: f"{event.agent_role}: thinking",
            EventType.TOOL_CALLED: f"Tool: {event.data.get('tool_name', 'unknown')}",
            EventType.TOOL_RESULT: f"Result from {event.data.get('tool_name', 'tool')}",
            EventType.FILE_CREATED: f"Created {event.data.get('path', 'file')}",
            EventType.FILE_MODIFIED: f"Modified {event.data.get('path', 'file')}",
            EventType.FILE_DELETED: f"Deleted {event.data.get('path', 'file')}",
            EventType.STEP_STARTED: f"Step started: {event.data.get('description', '')[:50]}",
            EventType.STEP_COMPLETED: f"Step completed",
            EventType.STEP_FAILED: f"Step failed: {event.data.get('error', '')[:50]}",
            EventType.CHECKPOINT: event.data.get("label", "Checkpoint"),
            EventType.USER_INTERVENTION: "User intervention",
        }
        return labels.get(event.event_type, event.event_type.value)


# Singleton
replay_service = ExecutionReplayService()
