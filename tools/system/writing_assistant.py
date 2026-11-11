"""
AI Writing Assistant for DesktopPilot AI (Phase 3 - Task 8).
Works inside any active Windows application (Notepad, Word, Browser, VS Code):
1. Copies selected text (`Ctrl+C`) or reads current clipboard.
2. Processes text with AI (Grammar fix, Professional rewrite, Email reply, Translation, Expansion).
3. Copies improved text back to clipboard and optionally pastes (`Ctrl+V`) into the active app.
"""

import asyncio
from typing import Dict, Any
from tools.desktop.native_input import native_desktop
from tools.system.clipboard_ai import clipboard_ai
from utils.logger import logger


class AIWritingAssistant:
    """
    In-app AI Writing Assistant that transforms selected/copied text.
    """

    @classmethod
    async def improve_text_in_app(
        cls,
        action: str = "professional",
        target_language: str = "Urdu",
        auto_paste: bool = False
    ) -> Dict[str, Any]:
        """
        Transforms clipboard or currently selected text and optionally pastes it back.
        action: 'grammar_fix' | 'professional' | 'email_reply' | 'translate' | 'summarize'
        """
        action_key = action.lower().strip()

        if action_key == "translate":
            res = await clipboard_ai.translate_clipboard(target_language=target_language)
            output_text = res.get("translation", "")
        elif action_key == "summarize":
            res = await clipboard_ai.summarize_clipboard()
            output_text = res.get("summary", "")
        else:
            res = await clipboard_ai.rewrite_clipboard(style=action_key)
            output_text = res.get("rewritten_text", "")

        if res.get("status") != "success":
            return res

        if auto_paste and output_text:
            await asyncio.sleep(0.2)
            native_desktop.hotkey("ctrl", "v")

        return {
            "status": "success",
            "action": action_key,
            "output_text": output_text,
            "auto_pasted": auto_paste,
            "message": res.get("message", f"Writing assistant completed ({action_key}).")
        }


writing_assistant = AIWritingAssistant()

