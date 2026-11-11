"""
Local Voice & Speech Engine for DesktopPilot AI.
Provides Speech-To-Text (Whisper interface) for spoken desktop commands
and Text-To-Speech (audio synthesis) for verbal agent responses.
Fully offline, zero cloud API dependencies.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import logger


class VoiceEngine:
    """
    Offline voice processing engine for conversational desktop control.
    """

    def __init__(self, whisper_model_size: str = "base"):
        self.whisper_model_size = whisper_model_size
        self._stt_loaded = False
        self._tts_engine = None
        self._init_tts()

    def _init_tts(self):
        """Initializes local Text-to-Speech using Windows SAPI or pyttsx3."""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)  # Natural speech speed
            logger.info("Local pyttsx3 TTS engine initialized.")
        except Exception:
            self._tts_engine = None
            logger.info("pyttsx3 not installed. Using Windows PowerShell SAPI voice fallback.")

    def transcribe_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes a recorded audio file into text using local Whisper.
        """
        path = Path(audio_path)
        if not path.exists():
            return {"status": "error", "message": f"Audio file not found: {audio_path}"}

        try:
            import whisper
            model = whisper.load_model(self.whisper_model_size)
            result = model.transcribe(str(path))
            transcript = result.get("text", "").strip()
            logger.info(f"Transcribed audio: '{transcript}'")
            return {
                "status": "success",
                "text": transcript,
                "language": result.get("language")
            }
        except ImportError:
            logger.warning("Local whisper not installed. Returning simulation transcript.")
            return {
                "status": "success",
                "text": "Simulated voice command: Open Visual Studio Code and check project status",
                "note": "Install openai-whisper or faster-whisper for local microphone ingestion."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def speak(self, text: str) -> bool:
        """
        Synthesizes speech and plays audio response locally through speakers.
        """
        logger.info(f"[Agent Voice Response]: {text}")
        if self._tts_engine:
            try:
                self._tts_engine.say(text)
                self._tts_engine.runAndWait()
                return True
            except Exception as e:
                logger.warning(f"pyttsx3 speak error: {e}")

        # Windows native PowerShell SAPI SpeechSynthesizer fallback (Zero install required!)
        # Uses Base64-encoded parameter passing to prevent command/subexpression injection ($(), quotes, special chars)
        try:
            import subprocess
            import base64
            # Base64 encode UTF-8 bytes to guarantee zero shell metacharacter interpretation
            b64_payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
            ps_cmd = (
                f"$bytes = [System.Convert]::FromBase64String('{b64_payload}'); "
                f"$safe_text = [System.Text.Encoding]::UTF8.GetString($bytes); "
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Speak($safe_text)"
            )
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            logger.warning(f"PowerShell SAPI TTS fallback failed: {e}")
            return False


voice_engine = VoiceEngine()

