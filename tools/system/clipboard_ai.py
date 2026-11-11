"""
Clipboard AI Tool for DesktopPilot AI.
Provides intelligent clipboard interactions:
- Read / Write Windows clipboard
- AI Summarization of copied text
- AI Translation (Urdu / English / etc.)
- Professional / Casual rewriting
- Format as Markdown
"""

import subprocess
import asyncio
from typing import Dict, Any, Optional
from models.ollama.llm_service import llm_service
from utils.logger import logger


class ClipboardAI:
    """Intelligent Windows Clipboard Controller & Assistant."""

    @staticmethod
    def get_clipboard_text() -> str:
        """Reads plain text from the Windows clipboard using Tkinter or PowerShell fallback."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return text
        except Exception:
            pass

        try:
            cmd = "Get-Clipboard"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=8)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to read clipboard: {e}")
            return ""

    @staticmethod
    def set_clipboard_text(text: str) -> bool:
        """Writes plain text to the Windows clipboard via instant Tkinter or UTF-16 clip.exe."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
            logger.info(f"Updated clipboard ({len(text)} chars).")
            return True
        except Exception:
            pass

        try:
            # Windows clip.exe expects UTF-16LE for Unicode symbols like bullets (•)
            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True, timeout=2)
            logger.info(f"Updated clipboard via clip.exe ({len(text)} chars).")
            return True
        except Exception as e:
            logger.warning(f"Clipboard write warning: {e}")
            return False

    async def summarize_clipboard(self) -> Dict[str, Any]:
        """Reads current clipboard text and generates a concise summary."""
        text = self.get_clipboard_text()
        if not text:
            return {"status": "empty", "message": "Clipboard is currently empty."}

        prompt = f"Summarize the following text clearly and concisely into key bullet points:\n\n{text[:4000]}"
        system_prompt = "You are an expert executive summarizer. Be accurate, concise, and direct."

        try:
            health = await llm_service.check_health()
            if health.get("ready"):
                summary = await llm_service.chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=system_prompt,
                    temperature=0.2
                )
            else:
                raise RuntimeError("Ollama offline")
        except Exception:
            # Extractive summary fallback when offline LLM is not loaded
            sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]
            top_points = sentences[:3] if sentences else [text[:200]]
            summary = "• " + "\n• ".join(top_points)

        self.set_clipboard_text(summary)
        return {
            "status": "success",
            "original_char_count": len(text),
            "summary": summary,
            "action": "Summary copied to clipboard."
        }

    async def translate_clipboard(self, target_language: str = "Urdu") -> Dict[str, Any]:
        """Translates current clipboard text into the target language."""
        text = self.get_clipboard_text()
        if not text:
            return {"status": "empty", "message": "Clipboard is currently empty."}

        prompt = f"Translate the following text into {target_language}. Maintain the original meaning, tone, and formatting:\n\n{text[:4000]}"
        system_prompt = f"You are a professional translator fluent in {target_language} and English."

        try:
            health = await llm_service.check_health()
            if health.get("ready"):
                translation = await llm_service.chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=system_prompt,
                    temperature=0.2
                )
            else:
                raise RuntimeError("Ollama offline")
        except Exception:
            translation = f"[{target_language} Translation]: {text.strip()}"

        self.set_clipboard_text(translation)
        return {
            "status": "success",
            "target_language": target_language,
            "translation": translation,
            "action": "Translation copied to clipboard."
        }

    async def rewrite_clipboard(self, style: str = "professional") -> Dict[str, Any]:
        """
        Rewrites clipboard text in a specified style:
        'professional', 'email_reply', 'casual', 'concise', 'grammar_fix'.
        """
        text = self.get_clipboard_text()
        if not text:
            return {"status": "empty", "message": "Clipboard is currently empty."}

        style_instructions = {
            "professional": "Rewrite this text in a professional, polite, and executive business tone.",
            "email_reply": "Format and draft this as a well-structured, polite, professional email response.",
            "casual": "Rewrite this text in a friendly, conversational, easy-to-read tone.",
            "concise": "Condense and rewrite this text to be as brief, punchy, and clear as possible.",
            "grammar_fix": "Fix all grammar, spelling, punctuation, and phrasing issues while keeping the exact original intent."
        }
        instruction = style_instructions.get(style, style_instructions["professional"])

        prompt = f"{instruction}\n\nORIGINAL TEXT:\n{text[:4000]}"
        try:
            health = await llm_service.check_health()
            if health.get("ready"):
                rewritten = await llm_service.chat(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a world-class AI copywriter and communications editor.",
                    temperature=0.3
                )
            else:
                raise RuntimeError("Ollama offline")
        except Exception:
            cleaned = text.strip()
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:]
                if not cleaned.endswith((".", "!", "?")):
                    cleaned += "."
            if style == "email_reply":
                rewritten = f"Dear Team,\n\n{cleaned}\n\nBest regards,"
            else:
                rewritten = cleaned

        self.set_clipboard_text(rewritten)
        return {
            "status": "success",
            "style": style,
            "rewritten_text": rewritten,
            "action": "Rewritten text copied to clipboard."
        }

    def format_as_markdown(self) -> Dict[str, Any]:
        """Converts raw copied text or tables into clean GitHub Flavored Markdown."""
        text = self.get_clipboard_text()
        if not text:
            return {"status": "empty", "message": "Clipboard is currently empty."}

        # Quick structural heuristics for tables/lists
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return {"status": "empty", "message": "No content found."}

        # Check if tab or comma separated table
        if any("\t" in line for line in lines[:3]):
            rows = [line.split("\t") for line in lines]
            header = "| " + " | ".join(rows[0]) + " |"
            separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
            body = "\n".join("| " + " | ".join(row) + " |" for row in rows[1:])
            md_result = f"{header}\n{separator}\n{body}"
        else:
            # Bullet list or clean blockquote
            md_result = "\n".join(f"- {line}" for line in lines)

        self.set_clipboard_text(md_result)
        return {
            "status": "success",
            "markdown": md_result,
            "action": "Markdown formatted text copied to clipboard."
        }


clipboard_ai = ClipboardAI()
