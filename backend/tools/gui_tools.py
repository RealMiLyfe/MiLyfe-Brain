"""GUI Tools — PyAutoGUI desktop automation."""

from typing import Optional


async def gui_action(action: str, x: int = 0, y: int = 0, text: str = "", key: str = "") -> str:
    """Perform GUI automation action.

    Args:
        action: click, type, key, screenshot, move
        x: X coordinate for mouse actions
        y: Y coordinate for mouse actions
        text: Text to type
        key: Key to press
    """
    try:
        import pyautogui

        pyautogui.FAILSAFE = True

        if action == "click":
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})"

        elif action == "type":
            pyautogui.typewrite(text, interval=0.02)
            return f"Typed: {text[:50]}"

        elif action == "key":
            pyautogui.press(key)
            return f"Pressed key: {key}"

        elif action == "screenshot":
            screenshot = pyautogui.screenshot()
            return f"Screenshot taken: {screenshot.size}"

        elif action == "move":
            pyautogui.moveTo(x, y)
            return f"Moved to ({x}, {y})"

        elif action == "hotkey":
            keys = key.split("+")
            pyautogui.hotkey(*keys)
            return f"Hotkey: {key}"

        else:
            return f"Unknown GUI action: {action}"

    except Exception as e:
        return f"GUI error: {str(e)}"


def register_gui_tools(registry):
    """Register GUI tools with the tool registry."""
    registry.register("gui_action", "Desktop GUI automation (PyAutoGUI)", gui_action, permission="approve",
                      params={"action": "click/type/key/screenshot/move/hotkey", "x": "X coord", "y": "Y coord", "text": "Text to type", "key": "Key to press"})
