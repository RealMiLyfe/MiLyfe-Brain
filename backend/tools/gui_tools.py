"""MiLyfe Brain — PyAutoGUI Desktop Automation Tools."""

from __future__ import annotations

from models.schemas import PermissionLevel


async def gui_action(
    action: str,
    x: int = 0,
    y: int = 0,
    text: str = "",
    key: str = "",
) -> str:
    """Perform GUI automation actions.

    Actions: click, doubleclick, rightclick, moveto, type, press,
             hotkey, screenshot, locate
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
    except ImportError:
        return "Error: pyautogui not available (no display)"
    except Exception as e:
        return f"GUI not available: {e}"

    try:
        if action == "click":
            pyautogui.click(x, y)
            return f"Clicked at ({x}, {y})"

        elif action == "doubleclick":
            pyautogui.doubleClick(x, y)
            return f"Double-clicked at ({x}, {y})"

        elif action == "rightclick":
            pyautogui.rightClick(x, y)
            return f"Right-clicked at ({x}, {y})"

        elif action == "moveto":
            pyautogui.moveTo(x, y)
            return f"Moved to ({x}, {y})"

        elif action == "type":
            if text:
                pyautogui.typewrite(text, interval=0.05)
                return f"Typed: {text[:50]}"
            return "Error: no text provided"

        elif action == "press":
            if key:
                pyautogui.press(key)
                return f"Pressed: {key}"
            return "Error: no key provided"

        elif action == "hotkey":
            if key:
                keys = key.split("+")
                pyautogui.hotkey(*keys)
                return f"Hotkey: {key}"
            return "Error: no key combo provided"

        elif action == "screenshot":
            import os
            os.makedirs("/workspace/.screenshots", exist_ok=True)
            path = "/workspace/.screenshots/gui_latest.png"
            pyautogui.screenshot(path)
            return f"Screenshot saved: {path}"

        elif action == "locate":
            # Get screen size info
            w, h = pyautogui.size()
            pos = pyautogui.position()
            return f"Screen: {w}x{h}, Mouse: {pos}"

        else:
            return f"Unknown action: {action}"

    except Exception as e:
        return f"GUI error: {e}"


def register_gui_tools(registry):
    """Register GUI automation tools."""
    registry.register(
        name="gui_action",
        handler=gui_action,
        category="GUI",
        description="Desktop GUI automation (click, type, press, screenshot)",
        parameters={
            "action": "str (click|type|press|hotkey|screenshot|locate)",
            "x": "int",
            "y": "int",
            "text": "str",
            "key": "str",
        },
        permission=PermissionLevel.APPROVE,
    )
