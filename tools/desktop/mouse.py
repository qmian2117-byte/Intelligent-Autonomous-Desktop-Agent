"""
Desktop Mouse Automation Tool for DesktopPilot AI.
Enforces safety boundaries, fail-safes, and smooth movement.
"""

from typing import Literal, Tuple
from utils.logger import logger

try:
    import pyautogui
    # PyAutoGUI fail-safe: Moving mouse to upper-left corner aborts execution
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
except ImportError:
    pyautogui = None


class MouseController:
    """Controls mouse actions on the local desktop environment."""

    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """Returns the primary screen dimensions (width, height)."""
        if pyautogui is None:
            return (1920, 1080)
        return pyautogui.size()

    @classmethod
    def move_to(cls, x: int, y: int, duration: float = 0.3) -> str:
        """Smoothly move mouse pointer to (x, y) coordinates."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        width, height = cls.get_screen_size()
        if not (0 <= x <= width and 0 <= y <= height):
            return f"Error: Coordinates ({x}, {y}) out of screen bounds ({width}x{height})."

        pyautogui.moveTo(x, y, duration=duration)
        return f"Mouse moved to ({x}, {y})."

    @classmethod
    def click(cls, x: int, y: int, button: Literal["left", "right", "middle"] = "left") -> str:
        """Move to (x, y) and perform a mouse click."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        move_res = cls.move_to(x, y)
        if move_res.startswith("Error"):
            return move_res

        pyautogui.click(x=x, y=y, button=button)
        logger.info(f"Mouse clicked at ({x}, {y}) with button '{button}'.")
        return f"Clicked ({x}, {y}) with {button} button."

    @classmethod
    def double_click(cls, x: int, y: int) -> str:
        """Perform a double click at (x, y)."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        cls.move_to(x, y)
        pyautogui.doubleClick(x=x, y=y)
        return f"Double-clicked at ({x}, {y})."

    @classmethod
    def scroll(cls, clicks: int) -> str:
        """Scroll vertical wheel up (positive) or down (negative)."""
        if pyautogui is None:
            return "Error: pyautogui is not installed."

        pyautogui.scroll(clicks)
        return f"Scrolled wheel by {clicks} units."

