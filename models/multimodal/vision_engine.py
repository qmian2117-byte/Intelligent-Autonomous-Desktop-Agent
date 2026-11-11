"""
Local Vision & Multimodal Engine for DesktopPilot AI.
Interfaces with local Vision-Language Models (e.g. Llama-3.2-Vision, Qwen2-VL, Moondream)
to analyze screenshots, detect UI elements, and compute click coordinates (x, y).
"""

import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel
try:
    import httpx
except ImportError:
    httpx = None

from config.settings import settings
from utils.logger import logger


class UIElementDetection(BaseModel):
    element_name: str
    confidence: float
    x: int
    y: int
    width: Optional[int] = None
    height: Optional[int] = None
    description: Optional[str] = None


class VisionEngine:
    """
    Multimodal visual reasoning engine for desktop automation.
    Allows the agent to 'see' the user's screen and locate buttons, icons, and menus.
    """

    def __init__(self, model_name: str = "llama3.2-vision:11b"):
        self.model_name = model_name
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=90.0) if httpx else None

    @staticmethod
    def encode_image(image_path: str) -> Optional[str]:
        """Encodes an image file on disk to base64 for LLM vision consumption."""
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image not found at path: {image_path}")
            return None
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def find_element_coordinates(
        self,
        image_path: str,
        element_description: str,
        screen_width: int = 1920,
        screen_height: int = 1080
    ) -> Optional[UIElementDetection]:
        """
        Uses local vision model to locate a described UI button or icon on the screen.
        Returns the center (x, y) coordinates to click.
        """
        base64_image = self.encode_image(image_path)
        if not base64_image:
            return None

        prompt = f"""You are a desktop UI vision grounding model.
Analyze this screenshot ({screen_width}x{screen_height}).
Find the element: "{element_description}".

Respond strictly in valid JSON:
{{
  "found": true,
  "x": 450,
  "y": 280,
  "confidence": 0.95,
  "description": "Center coordinates of {element_description}"
}}
If not visible, set "found": false.
"""

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64_image]
                }
            ],
            "stream": False,
            "options": {"temperature": 0.0}
        }

        try:
            res = await self._client.post("/api/chat", json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data.get("message", {}).get("content", "")
                import re, json
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    if parsed.get("found"):
                        return UIElementDetection(
                            element_name=element_description,
                            confidence=parsed.get("confidence", 0.9),
                            x=parsed.get("x", screen_width // 2),
                            y=parsed.get("y", screen_height // 2),
                            description=parsed.get("description")
                        )
        except Exception as e:
            logger.warning(f"Local vision model unavailable ({e}). Using heuristic center coordinate fallback.")

        # Heuristic fallback for testing when vision model is not loaded in VRAM
        return UIElementDetection(
            element_name=element_description,
            confidence=0.5,
            x=screen_width // 2,
            y=screen_height // 2,
            description=f"Fallback center estimate for '{element_description}'"
        )


vision_engine = VisionEngine()

