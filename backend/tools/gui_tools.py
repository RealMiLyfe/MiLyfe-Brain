"""
MiLyfe Brain - GUI Automation Tools

Desktop automation using PyAutoGUI.
"""
from __future__ import annotations

import base64
import io
from typing import TYPE_CHECKING

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

VALID_ACTIONS = {
    "click",
    "doubleclick",
    "type",
    "press",
    "hotkey",
    "screenshot",
    "locate",
    "moveto",
    "scroll",
}


def gui_action(
    action: str,
    x: int = 0,
    y: int = 0,
    text: str = "",
    key: str = "",
) -> str:
    """Perform a GUI action using PyAutoGUI.

    Args:
        action: Action type - click, doubleclick, type, press, hotkey, screenshot, locate, moveto, scroll.
        x: X coordinate for positional actions.
        y: Y coordinate for positional actions.
        text: Text for type/locate actions. For hotkey, comma-separated keys.
        key: Key name for press action.

    Returns:
        Action result or confirmation message.
    """
    if action not in VALID_ACTIONS:
        return f"Error: Invalid action '{action}'. Valid: {', '.join(sorted(VALID_ACTIONS))}"

    try:
        import pyautogui

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
    except ImportError:
        return "Error: PyAutoGUI not installed. Install with: pip install pyautogui"

    try:
        if action == "click":
            pyautogui.click(x=x, y=y)
            return f"Clicked at ({x}, {y})"

        elif action == "doubleclick":
            pyautogui.doubleClick(x=x, y=y)
            return f"Double-clicked at ({x}, {y})"

        elif action == "type":
            if not text:
                return "Error: 'text' parameter required for type action"
            if x or y:
                pyautogui.click(x=x, y=y)
            pyautogui.typewrite(text, interval=0.02)
            return f"Typed: '{text[:50]}{'...' if len(text) > 50 else ''}'"

        elif action == "press":
            if not key:
                return "Error: 'key' parameter required for press action"
            pyautogui.press(key)
            return f"Pressed: {key}"

        elif action == "hotkey":
            if not text:
                return "Error: 'text' parameter required (comma-separated keys) for hotkey action"
            keys = [k.strip() for k in text.split(",")]
            pyautogui.hotkey(*keys)
            return f"Hotkey: {' + '.join(keys)}"

        elif action == "screenshot":
            screenshot = pyautogui.screenshot()
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            buffer.seek(0)
            encoded = base64.b64encode(buffer.getvalue()).decode()
            return f"Screenshot captured ({screenshot.size[0]}x{screenshot.size[1]})\ndata:image/png;base64,{encoded[:100]}..."

        elif action == "locate":
            if not text:
                return "Error: 'text' parameter (image path) required for locate action"
            location = pyautogui.locateOnScreen(text, confidence=0.8)
            if location:
                center = pyautogui.center(location)
                return f"Found at: ({center.x}, {center.y}) [region: {location}]"
            else:
                return f"Image not found on screen: {text}"

        elif action == "moveto":
            pyautogui.moveTo(x=x, y=y, duration=0.3)
            return f"Moved cursor to ({x}, {y})"

        elif action == "scroll":
            # Use y as scroll amount (positive = up, negative = down)
            clicks = y if y else -3
            pyautogui.scroll(clicks, x=x)
            return f"Scrolled {clicks} clicks at x={x}"

        return f"Action '{action}' not implemented"

    except Exception as e:
        return f"GUI error: {type(e).__name__}: {e}"


def register_gui_tools(registry: ToolRegistry) -> None:
    """Register GUI automation tools with the tool registry."""
    registry.register(
        name="gui_action",
        handler=gui_action,
        category="gui",
        description="Perform desktop GUI actions (click, type, press, hotkey, screenshot, locate).",
        parameters={
            "action": {"type": "string", "description": "Action: click, doubleclick, type, press, hotkey, screenshot, locate, moveto, scroll", "required": True},
            "x": {"type": "integer", "description": "X coordinate", "default": 0},
            "y": {"type": "integer", "description": "Y coordinate", "default": 0},
            "text": {"type": "string", "description": "Text for type/hotkey/locate actions", "default": ""},
            "key": {"type": "string", "description": "Key name for press action", "default": ""},
        },
        permission=PermissionLevel.CRITICAL,
        returns="Action result or confirmation",
    )
