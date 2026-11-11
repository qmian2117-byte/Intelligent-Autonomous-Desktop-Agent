"""
Desktop Keyboard Automation Tool for DesktopPilot AI.
Provides typed text injection, hotkeys, and individual key presses.
"""

from typing import List, Union
from utils.logger import logger

try:
    import pyautogui
except ImportError:
    pyautogui = None


class KeyboardController:
    """Controls keyboard actions on the local desktop environment."""

    @staticmethod
    def type_text(text: str, interval: float = 0.05) -> str:
        """Types out a given string with human-like typing cadence."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        pyautogui.write(text, interval=interval)
        logger.info(f"Typed text: {text[:30]}... (length: {len(text)})")
        return f"Typed {len(text)} characters successfully."

    @staticmethod
    def press_key(key: str) -> str:
        """Presses and releases a single key (e.g. 'enter', 'tab', 'esc')."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        pyautogui.press(key.lower())
        logger.info(f"Pressed key: {key}")
        return f"Pressed '{key}' key."

    @staticmethod
    def hotkey(*keys: str) -> str:
        """Presses a combination of keys simultaneously (e.g. 'ctrl', 'alt', 't' or 'win', 'r')."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        normalized_keys = [k.lower().strip() for k in keys]
        pyautogui.hotkey(*normalized_keys)
        combo = "+".join(normalized_keys)
        logger.info(f"Triggered hotkey combo: {combo}")
        return f"Triggered hotkey '{combo}' successfully."

