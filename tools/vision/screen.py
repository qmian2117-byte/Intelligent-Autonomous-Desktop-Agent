"""
Screen capture and visual inspection tools for DesktopPilot AI.
Provides screenshot capture, screen resolution, and coordinate mapping.
"""

from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime
from PIL import Image
from utils.logger import logger

try:
    import pyautogui
except ImportError:
    pyautogui = None


SCREENSHOTS_DIR = Path("logs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class ScreenTools:
    """Screen capture and display geometry tools."""

    @staticmethod
    def get_resolution() -> Tuple[int, int]:
        """Returns primary display resolution (width, height)."""
        if pyautogui is None:
            return (1920, 1080)
        return pyautogui.size()

    @staticmethod
    def capture_screen(filename: Optional[str] = None) -> Dict[str, str]:
        """
        Captures full desktop screenshot and saves it locally for model inspection.
        """
        if pyautogui is None:
            return {"error": "pyautogui is not installed."}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_name = filename or f"screen_{timestamp}.png"
        target_path = SCREENSHOTS_DIR / target_name

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(target_path)
            logger.info(f"Screenshot saved to {target_path}")
            return {
                "status": "success",
                "path": str(target_path.resolve()),
                "dimensions": f"{screenshot.width}x{screenshot.height}",
            }
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return {"error": str(e)}


screen_tools = ScreenTools()

