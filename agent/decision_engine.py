"""
Intelligent AI Decision-Making & Intent Reasoning Engine for DesktopPilot AI.
Replaces brittle hardcoded if/else rules with:
1. LLM-based zero-shot semantic reasoning (when Ollama/Local LLM is available).
2. Advanced Fuzzy Semantic Intent Classifier (tolerant to typos like 'vlume low', Roman Urdu, Hindi, English, and slang).
3. Dynamic parameter extraction & action dispatching.
"""

import re
import difflib
import json
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field

from utils.logger import logger
from models.ollama.llm_service import llm_service
from api.websocket.stream import telemetry_manager


class IntentDecision(BaseModel):
    intent: str = Field(..., description="High-level intent category")
    tool_name: str = Field(..., description="Tool to execute from registry or autonomous pilot")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0)
    thought: str = Field(..., description="Agent reasoning explanation")
    is_multi_step: bool = False


class DecisionEngine:
    """
    Intelligent Agent Decision-Making Engine.
    Translates free-form natural language prompts into precise desktop actions.
    """

    # Semantic Concept Clusters (Multilingual: English, Roman Urdu, Hindi, Common Typos)
    CONCEPTS = {
        "VOLUME": [
            "volume", "vlume", "volum", "vol", "vlm", "sound", "snd", "audio", 
            "awaz", "awaaz", "awz", "speaker", "spkr", "shor"
        ],
        "DOWN": [
            "low", "down", "kam", "km", "ahista", "dhiimi", "dheemi", "decrease", 
            "reduce", "lower", "drop", "ghatao", "slow", "downward", "less"
        ],
        "UP": [
            "up", "high", "tez", "barhao", "badao", "increase", "raise", "boost", 
            "loud", "louder", "more", "full", "zyada", "chadhaye"
        ],
        "MUTE": [
            "mute", "silent", "chup", "band", "unmute", "khamosh", "shutup"
        ],
        "BRIGHTNESS": [
            "brightness", "brigtness", "brightnes", "brtness", "light", "screen light", 
            "display light", "noor", "roshni", "dim"
        ],
        "OPEN": [
            "open", "oepn", "opn", "opne", "launch", "lunch", "start", "run", 
            "khol", "kholo", "kholna", "chalao", "dikhao", "goto", "visit", "browse", "le jao"
        ],
        "SEARCH": [
            "search", "serch", "srch", "sarch", "find", "locate", "dhoond", 
            "dhoondo", "dhundo", "khojo", "kahan", "look", "lookup", "filter"
        ],
        "CLIPBOARD": [
            "clipboard", "clip", "copy", "copied", "pasted", "paste"
        ],
        "RECYCLE_BIN": [
            "recycle", "bin", "trash", "kachra", "safai", "empty", "purge", "clean"
        ],
        "POWER_LOCK": [
            "lock", "lockscreen", "screenlock", "workstation", "band karo"
        ],
        "SHUTDOWN": [
            "shutdown", "turn off", "power off", "band"
        ],
        "SLEEP": [
            "sleep", "sula", "suspend", "hibernate", "soja"
        ],
        "RESTART": [
            "restart", "restrart", "reboot", "rebot", "reset pc", "dobara chala"
        ],
        "SYSTEM_SPECS": [
            "status", "specs", "health", "ram", "memory", "usage", "pc status", "hardware"
        ],
        "ACTION_WORDS": [
            "type", "write", "likh", "likho", "calculate", "hisab", "calc", "enter", 
            "press", "click", "search on youtube", "browse"
        ],
        "ORGANIZE": [
            "organize", "organise", "sort", "arrange", "tartib", "clean folder", "sort files"
        ],
        "ZIP": [
            "zip", "compress", "archive", "tar"
        ],
        "UNZIP": [
            "unzip", "extract", "unpack", "decompress"
        ],
        "DOWNLOAD": [
            "download", "dwnload", "fetch", "save video", "yt-dlp"
        ],
        "MOVE": [
            "move", "shift", "transfer", "bhejo"
        ],
        "SCREENSHOT": [
            "screenshot", "screnshot", "screencap", "snap", "capture", "tasveer"
        ],
        "SCREEN_UNDERSTAND": [
            "explain screen", "what is on screen", "read screen", "ocr", "screen text"
        ]
    }

    def _has_concept(self, tokens: List[str], concept_key: str, threshold: float = 0.82) -> bool:
        """Checks if any token in prompt matches the concept cluster, prioritizing exact matches."""
        candidates = self.CONCEPTS.get(concept_key, [])
        # 1. Exact match check first
        token_set = set(t.lower() for t in tokens)
        candidate_set = set(c.lower() for c in candidates)
        if token_set & candidate_set:
            return True

        # 2. Fuzzy match only if no exact match
        for t in tokens:
            for cand in candidates:
                if len(t) >= 4 and len(cand) >= 4:
                    if difflib.SequenceMatcher(None, t, cand).ratio() >= threshold:
                        return True
        return False

    async def decide_action(self, user_prompt: str) -> IntentDecision:
        """
        Main decision-making entrypoint.
        First attempts LLM reasoning if available; otherwise uses semantic fuzzy reasoning.
        """
        prompt_clean = user_prompt.strip().rstrip(".?!")
        lower_prompt = prompt_clean.lower()
        tokens = re.findall(r"\w+", lower_prompt)

        # 1. Multi-Step Screen Action & Voice Query Detection:
        # e.g. "open notepad and type hello", "brouser open karo aur...", "kitne folder hai", "calculate 450*12"
        has_math_expr = bool(re.search(r"\d+\s*(?:\*|\+|\-|\/|plus|minus|into|times|multiply|divide|zarb|jama|manfi|taqseem|x)\s*\d+", lower_prompt))
        if "start tracking" in lower_prompt or has_math_expr or \
           any(k in lower_prompt for k in [
               "kitne", "how many", "brouser", "browser", "brawser", "versus", " match ",
               "calculate", "hisab", "calclator", "notpad", "notepad", "youtube pr", "google pr"
           ]) or \
           (any(k in lower_prompt for k in ["limerox", "limeox", "tracker"]) and "track" in lower_prompt and "start" in lower_prompt) or \
           any(w in lower_prompt for w in [" and ", " then ", "phir", "aur", " or "]) or \
           (self._has_concept(tokens, "ACTION_WORDS") and any(op in lower_prompt for op in ["*", "+", "/", "-", "type", "write", "likh", "likho"])):
            return IntentDecision(
                intent="AUTONOMOUS_WORKFLOW",
                tool_name="autonomous_screen_pilot",
                parameters={"goal": prompt_clean},
                confidence=0.95,
                thought=f"Detected multi-step physical computer operation from prompt: '{prompt_clean}'",
                is_multi_step=True
            )

        # 2. Fast High-Confidence Semantic Fuzzy Intent Reasoner (0.01s latency)
        semantic_decision = self._semantic_fuzzy_reasoning(prompt_clean, tokens)
        if semantic_decision.confidence >= 0.90:
            return semantic_decision

        # 3. Deep LLM Zero-Shot Reasoning (Llama 3.1 8B) for complex / open-ended prompts
        llm_decision = await self._try_llm_reasoning(prompt_clean)
        if llm_decision:
            return llm_decision

        return semantic_decision

    async def _try_llm_reasoning(self, prompt: str) -> Optional[IntentDecision]:
        """Queries local Ollama Llama 3.1 8B for zero-shot intent reasoning."""
        try:
            health = await llm_service.check_health()
            if not health.get("ready"):
                return None  # Ollama model not ready, proceed to fuzzy semantic layer

            system_prompt = """You are the AI Decision Engine of DesktopPilot.
Map the user prompt to the most accurate tool and extract parameters.
Output strictly JSON:
{
  "tool_name": "volume_up" | "volume_down" | "mute_volume" | "set_brightness" | "open_anything" | "search_files" | "clipboard_summarize" | "clipboard_translate" | "clipboard_rewrite" | "clipboard_format_markdown" | "empty_recycle_bin" | "lock_pc" | "sleep_pc" | "restart_pc" | "schedule_shutdown" | "cancel_shutdown" | "get_system_metrics" | "take_screenshot" | "explain_screen" | "extract_screen_text" | "organize_downloads" | "autonomous_screen_pilot",
  "parameters": {},
  "thought": "brief reasoning"
}"""
            response_text = await llm_service.chat(
                messages=[{"role": "user", "content": f"User prompt: '{prompt}'"}],
                system_prompt=system_prompt,
                temperature=0.1
            )
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return IntentDecision(
                    intent="LLM_RESOLVED",
                    tool_name=data.get("tool_name", "open_anything"),
                    parameters=data.get("parameters", {}),
                    confidence=0.98,
                    thought=f"[LLM Decision] {data.get('thought', 'Reasoned via Llama 3.1')}"
                )
        except Exception as e:
            logger.debug(f"LLM decision bypass ({e}) -> Using Semantic Fuzzy Layer.")
        return None

    def _semantic_fuzzy_reasoning(self, prompt: str, tokens: List[str]) -> IntentDecision:
        """
        Understands intent, typos (e.g. 'vlume low', 'awz km'), synonyms, and parameters.
        """
        # A. Volume Intent (Supports 'vlume low', 'awaz ahista', 'sound increase', 'volum down')
        if self._has_concept(tokens, "VOLUME"):
            if self._has_concept(tokens, "MUTE"):
                return IntentDecision(
                    intent="VOLUME_CONTROL",
                    tool_name="mute_volume",
                    parameters={},
                    confidence=0.95,
                    thought="Understood intent to toggle audio mute."
                )
            if self._has_concept(tokens, "DOWN"):
                return IntentDecision(
                    intent="VOLUME_CONTROL",
                    tool_name="volume_down",
                    parameters={"steps": 5},
                    confidence=0.95,
                    thought=f"Understood intent to lower volume from '{prompt}' (typo/synonym resolved)."
                )
            if self._has_concept(tokens, "UP"):
                return IntentDecision(
                    intent="VOLUME_CONTROL",
                    tool_name="volume_up",
                    parameters={"steps": 5},
                    confidence=0.95,
                    thought=f"Understood intent to increase volume from '{prompt}' (typo/synonym resolved)."
                )

        # B. Brightness Intent (e.g. 'brightness 40', 'screen noor kam', 'dim light')
        if self._has_concept(tokens, "BRIGHTNESS"):
            nums = re.findall(r"\d+", prompt)
            pct = int(nums[0]) if nums else (30 if self._has_concept(tokens, "DOWN") else 70)
            return IntentDecision(
                intent="BRIGHTNESS_CONTROL",
                tool_name="set_brightness",
                parameters={"percent": pct},
                confidence=0.92,
                thought=f"Understood brightness adjustment to {pct}% from '{prompt}'."
            )

        # C. Recycle Bin (e.g. 'empty recycle bin', 'trash saaf kro', 'bin khali')
        if self._has_concept(tokens, "RECYCLE_BIN") and (
            self._has_concept(tokens, "RECYCLE_BIN") or "clean" in prompt.lower() or "empty" in prompt.lower()
        ):
            if any(k in prompt.lower() for k in ["bin", "trash", "recycle", "kachra"]):
                return IntentDecision(
                    intent="SYSTEM_MAINTENANCE",
                    tool_name="empty_recycle_bin",
                    parameters={},
                    confidence=0.94,
                    thought="Understood request to empty the Windows Recycle Bin."
                )

        # D. Lock PC
        if self._has_concept(tokens, "POWER_LOCK") and any(k in prompt.lower() for k in ["pc", "computer", "screen", "workstation", "laptop"]):
            return IntentDecision(
                intent="SYSTEM_SECURITY",
                tool_name="lock_pc",
                parameters={},
                confidence=0.95,
                thought="Understood command to lock Windows workstation."
            )

        # E. Sleep / Restart / Shutdown
        if self._has_concept(tokens, "SLEEP"):
            return IntentDecision(
                intent="POWER_CONTROL",
                tool_name="sleep_pc",
                parameters={},
                confidence=0.96,
                thought="Understood command to put PC into Sleep mode."
            )

        if self._has_concept(tokens, "RESTART"):
            return IntentDecision(
                intent="POWER_CONTROL",
                tool_name="restart_pc",
                parameters={"delay_seconds": 10},
                confidence=0.96,
                thought="Understood command to restart the computer (typo tolerant: restart/restrart)."
            )

        if self._has_concept(tokens, "SHUTDOWN"):
            if "cancel" in prompt.lower() or "abort" in prompt.lower() or "rok" in prompt.lower():
                return IntentDecision(
                    intent="POWER_CONTROL",
                    tool_name="cancel_shutdown",
                    parameters={},
                    confidence=0.95,
                    thought="Understood request to cancel pending shutdown."
                )
            nums = re.findall(r"\d+", prompt)
            mins = int(nums[0]) if nums else 1
            return IntentDecision(
                intent="POWER_CONTROL",
                tool_name="schedule_shutdown",
                parameters={"minutes": mins},
                confidence=0.93,
                thought=f"Understood command to schedule PC shutdown in {mins} minute(s)."
            )

        # F. System Specs / RAM
        if self._has_concept(tokens, "SYSTEM_SPECS"):
            return IntentDecision(
                intent="SYSTEM_TELEMETRY",
                tool_name="get_system_metrics",
                parameters={},
                confidence=0.92,
                thought="Understood query regarding hardware/RAM memory metrics."
            )

        # F2. Screenshot & Screen Understanding (Phase 3)
        if self._has_concept(tokens, "SCREENSHOT"):
            return IntentDecision(
                intent="SCREEN_CAPTURE",
                tool_name="take_screenshot",
                parameters={"save_to_pictures": True},
                confidence=0.96,
                thought="Understood request to capture a desktop screenshot."
            )

        if any(k in prompt.lower() for k in ["explain screen", "what is on screen", "what's on my screen", "screen pr kya hai"]):
            return IntentDecision(
                intent="SCREEN_UNDERSTANDING",
                tool_name="explain_screen",
                parameters={},
                confidence=0.95,
                thought="Understood request to explain what is currently visible on screen."
            )

        if any(k in prompt.lower() for k in ["extract text", "read screen", "ocr screen", "copy text from image"]):
            return IntentDecision(
                intent="SCREEN_OCR",
                tool_name="extract_screen_text",
                parameters={},
                confidence=0.95,
                thought="Understood request to extract readable text from the current screen."
            )

        # G. Clipboard AI
        if self._has_concept(tokens, "CLIPBOARD") or "copied" in prompt.lower():
            if any(k in prompt.lower() for k in ["summarize", "khulasa", "summary", "short"]):
                return IntentDecision(
                    intent="CLIPBOARD_AI",
                    tool_name="clipboard_summarize",
                    parameters={},
                    confidence=0.95,
                    thought="Understood request to summarize copied clipboard text."
                )
            if any(k in prompt.lower() for k in ["translate", "tarjuma"]):
                target_lang = "English" if "english" in prompt.lower() else "Urdu"
                return IntentDecision(
                    intent="CLIPBOARD_AI",
                    tool_name="clipboard_translate",
                    parameters={"target_language": target_lang},
                    confidence=0.95,
                    thought=f"Understood request to translate clipboard to {target_lang}."
                )
            if any(k in prompt.lower() for k in ["markdown", "format", "table"]):
                return IntentDecision(
                    intent="CLIPBOARD_AI",
                    tool_name="clipboard_format_markdown",
                    parameters={},
                    confidence=0.95,
                    thought="Understood request to convert clipboard content into Markdown."
                )
            if any(k in prompt.lower() for k in ["rewrite", "grammar", "professional", "email"]):
                style = "email_reply" if "email" in prompt.lower() else "professional"
                return IntentDecision(
                    intent="CLIPBOARD_AI",
                    tool_name="clipboard_rewrite",
                    parameters={"style": style},
                    confidence=0.95,
                    thought="Understood request to polish/rewrite clipboard text."
                )

        # H. Downloads & Media
        if self._has_concept(tokens, "DOWNLOAD"):
            # Check for YouTube or web URL
            urls = re.findall(r"https?://[^\s]+", prompt)
            if urls:
                target_url = urls[0]
                if any(yt in target_url.lower() for yt in ["youtube.com", "youtu.be", "vimeo"]):
                    is_audio = "audio" in prompt.lower() or "mp3" in prompt.lower()
                    return IntentDecision(
                        intent="MEDIA_DOWNLOAD",
                        tool_name="download_media",
                        parameters={"url": target_url, "extract_audio": is_audio},
                        confidence=0.96,
                        thought=f"Understood request to download media from '{target_url}'."
                    )
                else:
                    return IntentDecision(
                        intent="FILE_DOWNLOAD",
                        tool_name="download_file",
                        parameters={"url": target_url},
                        confidence=0.96,
                        thought=f"Understood direct file download from '{target_url}'."
                    )
            if "organize" in prompt.lower() or "sort" in prompt.lower() or "safai" in prompt.lower():
                return IntentDecision(
                    intent="FOLDER_ORGANIZE",
                    tool_name="organize_downloads",
                    parameters={},
                    confidence=0.95,
                    thought="Understood request to auto-organize the Downloads folder."
                )

        # I. Smart File Management (Organize, Zip, Unzip, Move)
        if self._has_concept(tokens, "ORGANIZE"):
            target_folder = prompt.lower()
            for w in self.CONCEPTS["ORGANIZE"]:
                target_folder = target_folder.replace(w, "")
            target_folder = target_folder.replace("folder", "").replace("directory", "").strip() or "."
            if "download" in target_folder:
                return IntentDecision(
                    intent="FOLDER_ORGANIZE",
                    tool_name="organize_downloads",
                    parameters={},
                    confidence=0.95,
                    thought="Understood request to auto-organize Downloads folder."
                )
            return IntentDecision(
                intent="FOLDER_ORGANIZE",
                tool_name="folder_auto_organize",
                parameters={"target_dir": target_folder},
                confidence=0.92,
                thought=f"Understood request to organize directory: '{target_folder}'."
            )

        if self._has_concept(tokens, "ZIP"):
            clean_target = prompt.lower()
            for w in self.CONCEPTS["ZIP"]:
                clean_target = clean_target.replace(w, "")
            clean_target = clean_target.replace("this folder", ".").replace("folder", "").strip() or "."
            return IntentDecision(
                intent="FILE_COMPRESSION",
                tool_name="file_compress_zip",
                parameters={"target_path": clean_target},
                confidence=0.92,
                thought=f"Understood request to compress '{clean_target}' into a ZIP archive."
            )

        if self._has_concept(tokens, "UNZIP"):
            clean_target = prompt.lower()
            for w in self.CONCEPTS["UNZIP"]:
                clean_target = clean_target.replace(w, "")
            clean_target = clean_target.replace("file", "").replace("archive", "").strip()
            return IntentDecision(
                intent="FILE_EXTRACTION",
                tool_name="file_extract_zip",
                parameters={"zip_path": clean_target},
                confidence=0.92,
                thought=f"Understood request to extract ZIP archive '{clean_target}'."
            )

        if self._has_concept(tokens, "MOVE") and "to" in prompt.lower():
            # Check for "move all <ext> to <dest>"
            match = re.search(r"all\s+(\w+)\s+to\s+([a-zA-Z0-9_\-\\\/:\s]+)", prompt.lower())
            if match:
                ext = match.group(1).replace("files", "").replace("file", "").strip()
                dest = match.group(2).strip()
                return IntentDecision(
                    intent="FILE_MOVE",
                    tool_name="file_move_by_extension",
                    parameters={"source_dir": ".", "extension": ext, "destination_dir": dest},
                    confidence=0.94,
                    thought=f"Understood request to move all {ext} files to '{dest}'."
                )

        # J. Universal Launcher ("open <target>", "kholo <target>", "lunch <target>")
        if self._has_concept(tokens, "OPEN"):
            target = prompt.lower()
            for o_word in self.CONCEPTS["OPEN"]:
                target = re.sub(rf"\b{o_word}\b", "", target)
            target = target.replace("please", "").replace("app", "").replace("software", "").strip()

            if target:
                return IntentDecision(
                    intent="UNIVERSAL_LAUNCH",
                    tool_name="open_anything",
                    parameters={"target": target},
                    confidence=0.92,
                    thought=f"Resolved target to open: '{target}'"
                )

        # I. Search Files ("find <x>", "dhundo <x>", "search for <x>")
        if self._has_concept(tokens, "SEARCH"):
            # Extract query
            clean_q = prompt.lower()
            for s_word in self.CONCEPTS["SEARCH"]:
                clean_q = re.sub(rf"\b{s_word}\b", "", clean_q)
            clean_q = clean_q.replace("all", "").replace("files", "").replace("file", "").strip()

            ext = None
            for known_ext in ["pdf", "csv", "png", "jpg", "txt", "py", "xlsx", "docx"]:
                if known_ext in clean_q:
                    ext = known_ext
                    break

            return IntentDecision(
                intent="FILE_SEARCH",
                tool_name="search_files",
                parameters={"query": clean_q, "extension": ext},
                confidence=0.90,
                thought=f"Understood file search intent for query: '{clean_q}'"
            )

        # J. Short noun phrase fallback (e.g. 'spotify', 'chrome', 'calculator')
        if len(tokens) <= 2:
            return IntentDecision(
                intent="UNIVERSAL_LAUNCH",
                tool_name="open_anything",
                parameters={"target": prompt.strip()},
                confidence=0.85,
                thought=f"Assuming direct launch for: '{prompt.strip()}'"
            )

        # Fallback to Autonomous Screen Pilot
        return IntentDecision(
            intent="AUTONOMOUS_PILOT",
            tool_name="autonomous_screen_pilot",
            parameters={"goal": prompt},
            confidence=0.80,
            thought=f"Passing open-ended request to Autonomous Pilot: '{prompt}'"
        )


decision_engine = DecisionEngine()
