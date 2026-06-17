"""
Advanced Vision Systems - IoT, AR/VR, and Intelligence OS.

Wave 5-6 future capabilities providing:
- IoT device integration (sensor data, actuator control)
- AR/VR workspace (spatial computing interface)
- Intelligence OS (system-level Brain access)
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════
# IoT Integration
# ═══════════════════════════════════════════════════════════════════════

class DeviceType(str, Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CAMERA = "camera"
    DISPLAY = "display"
    SPEAKER = "speaker"
    MICROPHONE = "microphone"
    CUSTOM = "custom"


@dataclass
class IoTDevice:
    """Represents a connected IoT device."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    device_type: DeviceType = DeviceType.SENSOR
    protocol: str = "mqtt"  # mqtt, http, websocket, zigbee, zwave
    address: str = ""
    status: str = "offline"
    last_reading: Optional[Dict] = None
    last_seen: float = 0
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IoTBridge:
    """Bridge between MiLyfe Brain and IoT devices."""

    def __init__(self):
        self._devices: Dict[str, IoTDevice] = {}
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._data_buffer: Dict[str, List[Dict]] = {}

    def register_device(self, name: str, device_type: DeviceType, protocol: str, address: str, capabilities: List[str] = None) -> str:
        """Register an IoT device."""
        device = IoTDevice(
            name=name,
            device_type=device_type,
            protocol=protocol,
            address=address,
            capabilities=capabilities or [],
        )
        self._devices[device.id] = device
        return device.id

    async def read_sensor(self, device_id: str) -> Optional[Dict]:
        """Read current sensor value."""
        device = self._devices.get(device_id)
        if not device or device.status != "online":
            return None
        return device.last_reading

    async def send_command(self, device_id: str, command: str, params: Dict = None) -> bool:
        """Send command to an actuator."""
        device = self._devices.get(device_id)
        if not device or device.device_type != DeviceType.ACTUATOR:
            return False
        # Would send via appropriate protocol
        return True

    def subscribe(self, device_id: str, callback: Callable):
        """Subscribe to device data updates."""
        if device_id not in self._subscriptions:
            self._subscriptions[device_id] = []
        self._subscriptions[device_id].append(callback)

    async def ingest_data(self, device_id: str, data: Dict):
        """Ingest data from a device."""
        device = self._devices.get(device_id)
        if not device:
            return
        device.last_reading = data
        device.last_seen = time.time()
        device.status = "online"

        # Buffer data for analysis
        if device_id not in self._data_buffer:
            self._data_buffer[device_id] = []
        self._data_buffer[device_id].append({"timestamp": time.time(), **data})
        # Keep last 1000 readings
        self._data_buffer[device_id] = self._data_buffer[device_id][-1000:]

        # Notify subscribers
        for callback in self._subscriptions.get(device_id, []):
            await callback(device_id, data)

    def get_devices(self) -> List[Dict]:
        """List all registered devices."""
        return [
            {"id": d.id, "name": d.name, "type": d.device_type.value,
             "status": d.status, "last_seen": d.last_seen}
            for d in self._devices.values()
        ]

    def get_device_history(self, device_id: str, limit: int = 100) -> List[Dict]:
        """Get recent data history for a device."""
        return self._data_buffer.get(device_id, [])[-limit:]


# ═══════════════════════════════════════════════════════════════════════
# AR/VR Workspace
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SpatialObject:
    """An object in the AR/VR workspace."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    object_type: str = ""  # panel, node, agent_avatar, file, connection
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0, "z": 0})
    rotation: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0, "z": 0})
    scale: Dict[str, float] = field(default_factory=lambda: {"x": 1, "y": 1, "z": 1})
    data: Dict[str, Any] = field(default_factory=dict)
    interactive: bool = True
    visible: bool = True


class ARVRWorkspace:
    """Spatial computing workspace for AR/VR visualization."""

    def __init__(self):
        self._objects: Dict[str, SpatialObject] = {}
        self._layout: str = "orbital"  # orbital, grid, tree, freeform
        self._sessions: Dict[str, Dict] = {}

    def create_session(self, user_id: str, headset_type: str = "quest3") -> str:
        """Create a new AR/VR session."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "user_id": user_id,
            "headset": headset_type,
            "created_at": time.time(),
            "objects": [],
        }
        return session_id

    def add_object(self, session_id: str, obj_type: str, position: Dict[str, float], data: Dict = None) -> str:
        """Add an object to the spatial workspace."""
        obj = SpatialObject(
            object_type=obj_type,
            position=position,
            data=data or {},
        )
        self._objects[obj.id] = obj
        if session_id in self._sessions:
            self._sessions[session_id]["objects"].append(obj.id)
        return obj.id

    def update_object(self, object_id: str, position: Optional[Dict] = None, data: Optional[Dict] = None):
        """Update an object's position or data."""
        obj = self._objects.get(object_id)
        if obj:
            if position:
                obj.position = position
            if data:
                obj.data.update(data)

    def get_scene(self, session_id: str) -> Dict[str, Any]:
        """Get the full scene data for rendering."""
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return {
            "session_id": session_id,
            "layout": self._layout,
            "objects": [
                {
                    "id": obj_id,
                    **(self._objects[obj_id].__dict__ if obj_id in self._objects else {})
                }
                for obj_id in session.get("objects", [])
            ],
        }

    def layout_agents_spatial(self, agents: List[Dict]) -> List[Dict]:
        """Generate 3D positions for agent avatars."""
        import math
        positioned = []
        count = len(agents)
        for i, agent in enumerate(agents):
            angle = (2 * math.pi * i) / count
            radius = 3.0
            positioned.append({
                **agent,
                "position": {
                    "x": radius * math.cos(angle),
                    "y": 1.5,
                    "z": radius * math.sin(angle),
                },
            })
        return positioned


# ═══════════════════════════════════════════════════════════════════════
# Intelligence OS
# ═══════════════════════════════════════════════════════════════════════

class IntelligenceOS:
    """System-level Brain access - Intelligence Operating System.

    Provides OS-level integration:
    - File system monitoring (daemon)
    - System notifications
    - Clipboard intelligence
    - Application context awareness
    - Voice commands
    - System-wide search
    """

    def __init__(self):
        self._watchers: Dict[str, Dict] = {}
        self._clipboard_history: List[Dict] = []
        self._voice_commands: Dict[str, Callable] = {}
        self._system_hooks: List[Dict] = []
        self._running = False

    async def start(self):
        """Start the Intelligence OS layer."""
        self._running = True

    async def stop(self):
        """Stop the Intelligence OS layer."""
        self._running = False

    def register_voice_command(self, trigger: str, handler: Callable):
        """Register a voice-activated command."""
        self._voice_commands[trigger.lower()] = handler

    async def process_voice(self, transcript: str) -> Optional[str]:
        """Process a voice command transcript."""
        transcript_lower = transcript.lower().strip()
        for trigger, handler in self._voice_commands.items():
            if trigger in transcript_lower:
                result = await handler(transcript)
                return str(result)
        return None

    def watch_directory(self, path: str, callback: Callable):
        """Watch a directory for changes."""
        watch_id = str(uuid.uuid4())
        self._watchers[watch_id] = {
            "path": path,
            "callback": callback,
            "created_at": time.time(),
        }
        return watch_id

    async def clipboard_changed(self, content: str, content_type: str = "text"):
        """Handle clipboard change event."""
        self._clipboard_history.append({
            "content": content[:1000],  # Limit stored size
            "type": content_type,
            "timestamp": time.time(),
        })
        # Keep last 100 entries
        self._clipboard_history = self._clipboard_history[-100:]

    async def system_search(self, query: str, scope: str = "workspace") -> List[Dict]:
        """System-wide intelligent search."""
        # Would integrate with OS-level search APIs
        results = []
        # Placeholder for actual implementation
        return results

    def get_context(self) -> Dict[str, Any]:
        """Get current system context for agent awareness."""
        return {
            "running": self._running,
            "active_watchers": len(self._watchers),
            "clipboard_entries": len(self._clipboard_history),
            "voice_commands": list(self._voice_commands.keys()),
            "last_clipboard": self._clipboard_history[-1] if self._clipboard_history else None,
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "watchers": len(self._watchers),
            "clipboard_history_size": len(self._clipboard_history),
            "registered_voice_commands": len(self._voice_commands),
        }
