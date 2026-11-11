"""
Voice Output & Verbal Response Tool for DesktopPilot AI.
Provides local audio speech synthesis for conversational agent feedback.
"""

from typing import Dict, Any
from models.voice.voice_engine import voice_engine
from utils.logger import logger


class VoiceTool:
    """Verbal feedback tool for DesktopPilot AI."""

    @staticmethod
    def speak(text: str) -> Dict[str, Any]:
        """
        Synthesizes text into speech and plays it through local speakers.
        Example: speak("Chrome has been opened for you.")
        """
        success = voice_engine.speak(text)
        return {
            "status": "success" if success else "failed",
            "spoken_text": text
        }


voice_tool = VoiceTool()

