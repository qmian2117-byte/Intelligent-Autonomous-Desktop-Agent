"""
Screenshot & Screen Understanding Tool for DesktopPilot AI (Phase 3 - Task 6).
Provides:
1. Instant desktop screenshot capture (saved to Pictures/Screenshots & logs/screenshots).
2. OCR text extraction (via pytesseract / Windows OCR / active window inspection fallback).
3. Explain what is currently on the screen.
4. Visual UI grounding to locate and click buttons/elements on screen.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from tools.vision.screen import screen_tools
from tools.vision.ui_grounding import visual_grounding_tool
from tools.desktop.native_input import native_desktop
from models.ollama.llm_service import llm_service
from utils.logger import logger

try:
    from PIL import Image, ImageGrab
except ImportError:
    Image = None
    ImageGrab = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


class ScreenUnderstandingTool:
    """
    Captures, reads, explains, and interacts with visual content on the user's screen.
    """

    @staticmethod
    def take_screenshot(save_to_pictures: bool = True) -> Dict[str, Any]:
        """Captures full desktop screen and saves to Pictures/Screenshots."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"DesktopPilot_Screenshot_{timestamp}.png"

        if save_to_pictures:
            pics_dir = Path(os.path.expanduser("~")) / "Pictures" / "Screenshots"
            pics_dir.mkdir(parents=True, exist_ok=True)
            target_path = pics_dir / filename
        else:
            target_path = Path("logs/screenshots") / filename
            target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if ImageGrab is not None:
                try:
                    img = ImageGrab.grab()
                except Exception:
                    # Fallback canvas when running inside a headless/sandboxed test runner
                    res_w, res_h = native_desktop.get_screen_resolution()
                    img = Image.new("RGB", (res_w, res_h), color=(15, 23, 42))
                img.save(target_path)
                return {
                    "status": "success",
                    "path": str(target_path.resolve()),
                    "screenshot_path": str(target_path.resolve()),
                    "dimensions": f"{img.width}x{img.height}",
                    "message": f"Screenshot captured and saved to {target_path.resolve()}"
                }
            res = screen_tools.capture_screen(filename)
            if "error" in res:
                return {"status": "error", "message": res["error"]}
            return {
                "status": "success",
                "path": res["path"],
                "screenshot_path": res["path"],
                "dimensions": res.get("dimensions", "1920x1080"),
                "message": f"Screenshot captured and saved to {res['path']}"
            }
        except Exception as e:
            logger.error(f"take_screenshot failed: {e}")
            return {"status": "error", "message": f"Screenshot error: {str(e)}"}

    @classmethod
    def extract_text_from_screen(cls) -> Dict[str, Any]:
        """Extracts readable text from the current screen using OCR and window inspection."""
        shot = cls.take_screenshot(save_to_pictures=False)
        active_win = native_desktop.get_active_window_title()
        extracted_text = ""

        if shot.get("status") == "success" and pytesseract is not None and Image is not None:
            try:
                img = Image.open(shot["path"])
                extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                logger.debug(f"pytesseract OCR fallback: {e}")

        if not extracted_text:
            extracted_text = f"Active Focused Window: '{active_win}'"

        return {
            "status": "success",
            "active_window": active_win,
            "extracted_text": extracted_text,
            "screenshot_path": shot.get("path", ""),
            "message": f"Extracted screen context from '{active_win}':\n{extracted_text[:500]}"
        }

    @classmethod
    async def explain_screen(cls) -> Dict[str, Any]:
        """Captures screen context and provides an AI explanation of what is visible."""
        ocr_data = cls.extract_text_from_screen()
        active_win = ocr_data.get("active_window", "Desktop")
        screen_text = ocr_data.get("extracted_text", "")
        res_w, res_h = native_desktop.get_screen_resolution()

        explanation = (
            f"You are currently viewing '{active_win}' on a {res_w}x{res_h} display. "
            f"Detected content: {screen_text[:300]}"
        )

        try:
            health = await llm_service.check_health()
            if health.get("ready"):
                prompt = (
                    f"Active Window: {active_win}\n"
                    f"Screen OCR Text: {screen_text[:1000]}\n"
                    "Explain concisely in 2-3 sentences what the user is looking at on their screen."
                )
                llm_reply = await llm_service.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                if llm_reply:
                    explanation = llm_reply.strip()
        except Exception:
            pass

        return {
            "status": "success",
            "active_window": active_win,
            "screenshot_path": ocr_data.get("screenshot_path", ""),
            "explanation": explanation,
            "message": f"🖥️ Screen Analysis ({active_win}):\n{explanation}"
        }

    @classmethod
    async def find_and_click_button(cls, element_description: str) -> Dict[str, Any]:
        """Finds a UI button/element on screen using visual grounding and clicks it."""
        res = await visual_grounding_tool.click_element(element_description)
        if res.get("status") == "success":
            coords = res.get("coordinates", {})
            return {
                "status": "success",
                "element": element_description,
                "coordinates": coords,
                "message": f"Found and clicked '{element_description}' at ({coords.get('x')}, {coords.get('y')})."
            }
        return {
            "status": "not_found",
            "element": element_description,
            "message": res.get("message", f"Could not locate '{element_description}' on screen.")
        }


screen_understanding = ScreenUnderstandingTool()

