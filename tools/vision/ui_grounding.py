"""
Visual Grounding Tool for DesktopPilot AI.
Combines screenshot capture with the multimodal vision engine to locate and click UI elements.
"""

from typing import Dict, Any, Optional
from tools.vision.screen import screen_tools
from tools.desktop.mouse import MouseController
from models.multimodal.vision_engine import vision_engine
from utils.logger import logger


class VisualGroundingTool:
    """
    Locates UI buttons, icons, or text on the screen using visual reasoning and clicks them.
    """

    @classmethod
    async def click_element(cls, description: str) -> Dict[str, Any]:
        """
        Takes a screenshot, uses the local vision model to find the element, and clicks it.
        Example: click_element("Search button in Chrome")
        """
        # 1. Capture screen
        capture_res = screen_tools.capture_screen()
        if "error" in capture_res:
            return {"status": "error", "message": f"Screen capture failed: {capture_res['error']}"}

        screenshot_path = capture_res["path"]
        width, height = screen_tools.get_resolution()

        logger.info(f"Visual Grounding: Searching for '{description}' in {screenshot_path}...")

        # 2. Local vision grounding inference
        detection = await vision_engine.find_element_coordinates(
            image_path=screenshot_path,
            element_description=description,
            screen_width=width,
            screen_height=height
        )

        if not detection:
            return {
                "status": "not_found",
                "message": f"Could not visually locate '{description}' on the screen."
            }

        # 3. Execute mouse click at detected coordinates
        click_res = MouseController.click(detection.x, detection.y)
        logger.info(f"Visual Grounding Clicked: ({detection.x}, {detection.y}) with confidence {detection.confidence}")

        return {
            "status": "success",
            "element": description,
            "coordinates": {"x": detection.x, "y": detection.y},
            "confidence": detection.confidence,
            "action_result": click_res
        }


visual_grounding_tool = VisualGroundingTool()

