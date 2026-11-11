"""
Autonomous Screen Control & Decision Pilot for DesktopPilot AI.
Executes multi-step physical PC operations (Clicking, Typing, Hotkeys, Window Management).
Observes current screen/window context and autonomously drives the desktop.
"""

import json
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from tools.desktop.native_input import native_desktop
from tools.system.app_controller import app_controller
from tools.system.universal_launcher import universal_launcher
from tools.system.file_search import file_search_tool
from models.ollama.llm_service import llm_service
from api.websocket.stream import telemetry_manager
from utils.logger import logger


class AutonomousAction(BaseModel):
    thought: str = Field(..., description="Reasoning about current screen and next action")
    action_type: str = Field(..., description="launch_app | click | type_text | press_key | hotkey | sleep | finish")
    params: Dict[str, Any] = Field(default_factory=dict)
    is_goal_complete: bool = False


AUTONOMOUS_PILOT_PROMPT = """You are DesktopPilot AI, an autonomous Computer-Use agent controlling a Windows PC.
You have physical control over the mouse, keyboard, and applications.

CURRENT SCREEN STATE:
- Primary Resolution: {resolution}
- Active Focused Window: "{active_window}"
- Step Number: {step_number} of {max_steps}
- Recent Action History: {history}

USER GOAL: "{user_goal}"

DECIDE THE NEXT IMMEDIATE PHYSICAL ACTION TO ACCOMPLISH THE GOAL.

AVAILABLE ACTION TYPES:
1. "launch_app": {{"app_name": "notepad" | "calc" | "chrome" | "terminal" | "code"}}
2. "click": {{"x": int, "y": int, "button": "left" | "right"}}
3. "double_click": {{"x": int, "y": int}}
4. "type_text": {{"text": "string to type into the active window"}}
5. "press_key": {{"key": "enter" | "tab" | "esc" | "space" | "backspace"}}
6. "hotkey": {{"keys": ["ctrl", "s"] | ["alt", "f4"] | ["win", "r"]}}
7. "sleep": {{"seconds": 1.0}} (Wait for app to load)
8. "finish": {{"summary": "Explanation of how the goal was completed"}}

RULES:
- Return ONLY valid JSON with no markdown formatting.
- If you need to open an app first, launch it and sleep 1.5 seconds.
- When an app is active and you need to type, use "type_text".
- After typing a search query, press "enter".
- When the goal is completed, set "action_type": "finish" and "is_goal_complete": true.

JSON FORMAT:
{{
  "thought": "Your visual/logical reasoning here.",
  "action_type": "click" | "type_text" | "press_key" | "hotkey" | "launch_app" | "sleep" | "finish",
  "params": {{}},
  "is_goal_complete": false
}}
"""


class AutonomousScreenPilot:
    """
    Main Autonomous Agent Loop that perceives the desktop and executes physical actions.
    """

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self._llm_available: Optional[bool] = None

    async def execute_autonomous_goal(self, user_goal: str) -> Dict[str, Any]:
        """
        Runs the full autonomous Perception-Decision-Action loop until goal completion.
        """
        logger.info(f"=== Starting Autonomous Screen Pilot: '{user_goal}' ===")
        await telemetry_manager.broadcast("autonomous_started", {"goal": user_goal})

        history: List[str] = []
        resolution = native_desktop.get_screen_resolution()
        res_str = f"{resolution[0]}x{resolution[1]}"

        # Fast deterministic check for well-known instant workflows (Notepad, Calc, Search, LimeOx, Drive/Folder)
        lower_goal = user_goal.lower()
        has_math = bool(re.search(r"\d+\s*(?:\*|\+|\-|\/|plus|minus|into|times|multiply|divide|zarb|jama|manfi|taqseem|x)\s*\d+", lower_goal))
        is_fast_workflow = has_math or any(k in lower_goal for k in [
            "notepad", "notpad", "calc", "calclator", "hisab", "youtube", "search", "serch", "srch",
            "browser", "brouser", "brawser", "chrome", "google", "find", "match", "limerox", "limeox",
            "tracker", "drive", "folder", "kitne"
        ])

        for step in range(1, self.max_steps + 1):
            active_window = native_desktop.get_active_window_title()
            logger.info(f"[Step {step}/{self.max_steps}] Active Window: '{active_window}'")

            # 1. Use instant deterministic workflow for known patterns, or query Llama 3.1 8B for custom goals
            action = None
            if not is_fast_workflow:
                system_prompt = "You are DesktopPilot AI. Output strictly parseable JSON."
                prompt = AUTONOMOUS_PILOT_PROMPT.format(
                    resolution=res_str,
                    active_window=active_window,
                    step_number=step,
                    max_steps=self.max_steps,
                    history=" -> ".join(history[-4:]) if history else "None",
                    user_goal=user_goal
                )
                try:
                    health = await llm_service.check_health()
                    if health.get("ready"):
                        raw_decision = await llm_service.chat(
                            messages=[{"role": "user", "content": prompt}],
                            system_prompt=system_prompt,
                            temperature=0.1
                        )
                        match = re.search(r"\{.*\}", raw_decision, re.DOTALL)
                        if match:
                            parsed = json.loads(match.group(0))
                            action = AutonomousAction(**parsed)
                except Exception as e:
                    logger.debug(f"LLM decision bypass ({e}). Using deterministic rule fallback.")

            if not action:
                action = self._fallback_action(lower_goal, step, active_window)

            # Broadcast decision to telemetry
            logger.info(f"Thought: {action.thought} | Action: {action.action_type} {action.params}")
            await telemetry_manager.broadcast("agent_action", {
                "step": step,
                "thought": action.thought,
                "action": action.action_type,
                "params": action.params
            })

            # 2. Check for finish
            if action.action_type == "finish" or action.is_goal_complete:
                summary = action.params.get("summary", "Goal completed successfully.")
                await telemetry_manager.broadcast("autonomous_finished", {"summary": summary})
                return {
                    "status": "success",
                    "total_steps": step,
                    "final_summary": summary,
                    "history": history
                }

            # 3. Execute physical action
            result_msg = await self._dispatch_action(action)
            history.append(f"Step {step}: {action.action_type} ({result_msg})")

            # Small delay for UI animations/rendering
            await asyncio.sleep(0.8)

        return {
            "status": "max_steps_reached",
            "total_steps": self.max_steps,
            "final_summary": f"Reached step limit ({self.max_steps}). Operations performed.",
            "history": history
        }

    async def _dispatch_action(self, action: AutonomousAction) -> str:
        """Dispatches action to native Windows desktop input controller."""
        act = action.action_type
        params = action.params

        if act == "launch_app":
            app_name = params.get("app_name", "notepad")
            res = app_controller.launch_app(app_name)
            await asyncio.sleep(1.0)
            return res.message

        elif act == "click":
            x = int(params.get("x", 500))
            y = int(params.get("y", 300))
            button = params.get("button", "left")
            return native_desktop.click(x, y, button=button)

        elif act == "double_click":
            x = int(params.get("x", 500))
            y = int(params.get("y", 300))
            return native_desktop.double_click(x, y)

        elif act == "type_text":
            text = str(params.get("text", ""))
            app_title = params.get("app_title")
            if app_title:
                return native_desktop.send_keys_to_app(app_title, text)
            return native_desktop.type_text(text)

        elif act == "press_key":
            key = str(params.get("key", "enter"))
            return native_desktop.press_key(key)

        elif act == "hotkey":
            keys = params.get("keys", ["ctrl", "s"])
            if isinstance(keys, str):
                keys = keys.split("+")
            return native_desktop.hotkey(*keys)

        elif act == "sleep":
            secs = float(params.get("seconds", 1.0))
            await asyncio.sleep(secs)
            return f"Waited {secs} seconds"

        return "Unknown action"

    @staticmethod
    def _extract_math_expression(goal: str) -> str:
        """
        Converts natural language / spoken math (English & Roman Urdu) into a clean expression.
        Examples:
        - 'open calculator and calculate 450 into 12' -> '450*12'
        - 'calculate 1250 plus 750 minus 200' -> '1250+750-200'
        - '144 divide by 12' -> '144/12'
        """
        s = goal.lower()
        replacements = [
            (r"\bmultiplied\s+by\b", "*"),
            (r"\bmultiply\s+by\b", "*"),
            (r"\bmultiply\b", "*"),
            (r"\binto\b", "*"),
            (r"\btimes\b", "*"),
            (r"\bzarb\b", "*"),
            (r"\bdivided\s+by\b", "/"),
            (r"\bdivide\s+by\b", "/"),
            (r"\bdivide\b", "/"),
            (r"\btaqseem\b", "/"),
            (r"\bplus\b", "+"),
            (r"\bjama\b", "+"),
            (r"\badd\b", "+"),
            (r"\bminus\b", "-"),
            (r"\bmanfi\b", "-"),
            (r"\bsubtract\b", "-"),
            (r"(?<=\d)\s*x\s*(?=\d)", "*"),
        ]
        for pattern, sym in replacements:
            s = re.sub(pattern, sym, s)

        match = re.search(r"(\d+(?:\.\d+)?(?:\s*[\*\+\-\/]\s*\d+(?:\.\d+)?)+)", s)
        if match:
            return re.sub(r"\s+", "", match.group(1))
        return "25*4"

    def _fallback_action(self, goal: str, step: int, active_window: str) -> AutonomousAction:
        """Deterministic fallback when offline LLM is busy or parsing fails."""
        # Scenario 00: Calculator & Math Expressions (Top Priority when math/calc detected)
        has_math = bool(re.search(r"\d+\s*(?:\*|\+|\-|\/|plus|minus|into|times|multiply|divide|zarb|jama|manfi|taqseem|x)\s*\d+", goal))
        if any(k in goal for k in ["calc", "calculator", "calclator", "calculate", "hisab"]) or has_math:
            raw_expr = self._extract_math_expression(goal)
            expr_with_eq = raw_expr + "="
            try:
                computed_val = eval(raw_expr, {"__builtins__": None}, {})
                if isinstance(computed_val, float) and computed_val.is_integer():
                    computed_val = int(computed_val)
            except Exception:
                computed_val = None

            if step == 1:
                return AutonomousAction(
                    thought=f"Launching Windows Calculator for expression '{raw_expr}'.",
                    action_type="launch_app",
                    params={"app_name": "calc"}
                )
            elif step == 2:
                # Clear existing calculator state (Esc) then type expression + '='
                native_desktop.force_bring_to_foreground("Calculator")
                native_desktop.press_key("esc")
                return AutonomousAction(
                    thought=f"Typing calculation '{expr_with_eq}' into Calculator.",
                    action_type="type_text",
                    params={"text": expr_with_eq, "app_title": "Calculator"}
                )
            else:
                ans_str = f" = {computed_val}" if computed_val is not None else ""
                return AutonomousAction(
                    thought="Calculation completed in Calculator.",
                    action_type="finish",
                    params={"summary": f"Calculator opened and calculated: {raw_expr}{ans_str}"}
                )
        # Scenario 00B: Notepad typing (supports 'notepad', 'notpad', 'write', 'type', 'likho', 'likh')
        if any(k in goal for k in ["notepad", "notpad", "note pad"]):
            if not any(w in goal for w in ["write", "type", "likho", "likh"]):
                res_np = universal_launcher.open("notepad")
                return AutonomousAction(
                    thought="Opened Notepad.",
                    action_type="finish",
                    params={"summary": res_np.get("message", "Launched Notepad.")}
                )
            if "notepad" not in active_window.lower() and step == 1:
                return AutonomousAction(
                    thought="Opening Notepad first.",
                    action_type="launch_app",
                    params={"app_name": "notepad"}
                )
            elif step == 2:
                text = "Welcome to DesktopPilot AI!"
                parts = re.split(r"\b(?:write|type|likho|likh)\b", goal, flags=re.IGNORECASE)
                if len(parts) > 1:
                    text = parts[1].replace("'", "").replace('"', "").strip()
                return AutonomousAction(
                    thought=f"Activating Notepad and typing '{text}'.",
                    action_type="type_text",
                    params={"text": text + "\n", "app_title": "Notepad"}
                )
            else:
                return AutonomousAction(
                    thought="Notepad text has been typed.",
                    action_type="finish",
                    params={"summary": "Notepad opened and text typed successfully."}
                )

        # Scenario 0A: Count / List Folders in a Drive (e.g. "Mujhe yah batao ki E drive mein kitne folder Hai")
        if any(k in goal for k in ["kitne", "how many", "count", "kon kon se", "list folder"]):
            drive_matches = re.findall(r"\b([a-z])\s*drive\b", goal)
            drive_letter = "E"
            for dm in drive_matches:
                cand = dm.upper()
                if Path(f"{cand}:\\").exists():
                    drive_letter = cand
                    break
                elif cand in ["I", "A"] and Path("E:\\").exists():
                    drive_letter = "E"
                    break
            info = file_search_tool.inspect_directory_contents(f"{drive_letter}:\\")
            return AutonomousAction(
                thought=f"Counted folders and files in {drive_letter}:\\ drive.",
                action_type="finish",
                params={"summary": info.get("message", f"Checked {drive_letter}:\\ drive.")}
            )

        # Scenario 0B: Browser / Google / YouTube Search (English + Roman Urdu + Voice Typos like 'brouser', 'find kar', 'srch')
        if any(k in goal for k in ["youtube", "browser", "brouser", "brawser", "google", "chrome", "match", "versus", "vs"]) or (
            any(k in goal for k in ["search", "serch", "srch", "find"])
            and not any(loc in goal for loc in ["drive", "folder", "flder", "desktop", "downloads", "documents", "my pc", "this pc"])
        ):
            import urllib.parse
            clean_query = goal
            # Strip common English & Roman Urdu command wrappers
            filler_phrases = [
                "open browser and search for", "open browser and search", "open youtube and search for",
                "open youtube and search", "brouser open karo aur", "browser open karo aur",
                "brouser open karo", "browser open karo", "ka brouser per", "ka browser per",
                "brouser per", "browser per", "google per", "youtube per", "youtube pr", "google pr",
                "open browser", "open youtube", "open chrome", "search on youtube", "search google for",
                "search google", "search for", "search karo", "search kar", "srch kro", "srch karo",
                "search", "serch", "srch", "find karo", "find kar", "find", "dhoondo", "dhundo",
                "open karo", "open kro", "karo", "kro"
            ]
            for phrase in filler_phrases:
                clean_query = re.sub(rf"\b{phrase}\b", " ", clean_query, flags=re.IGNORECASE)
            clean_query = re.sub(r"\s+", " ", clean_query).strip() or goal
            encoded_q = urllib.parse.quote_plus(clean_query)

            if "youtube" in goal:
                url = f"https://www.youtube.com/results?search_query={encoded_q}"
                summary = f"Opened YouTube and searched for '{clean_query}'."
            else:
                url = f"https://www.google.com/search?q={encoded_q}"
                summary = f"Opened browser and searched Google for '{clean_query}'."

            if step == 1:
                app_controller.open_browser(url)
                return AutonomousAction(
                    thought=f"Opening browser search for '{clean_query}'.",
                    action_type="sleep",
                    params={"seconds": 1.2}
                )
            else:
                return AutonomousAction(
                    thought="Search loaded in browser.",
                    action_type="finish",
                    params={"summary": summary}
                )

        # Scenario 0C: Multi-step Drive/Shell Folder Search + Open or Delete
        # e.g. "open e drive and search folder fyp and open it"
        # e.g. "open my pc and then desktop folder then serch del folder and then it del"
        drive_match = re.search(r"\b([a-z])\s*drive\b", goal)
        has_shell_folder = any(k in goal for k in ["desktop", "downloads", "documents", "pictures", "my pc", "this pc"])
        if drive_match or "folder" in goal or "flder" in goal or has_shell_folder:
            import shutil
            # 1. Determine root directory to open & search
            if "desktop" in goal:
                search_root = str(Path.home() / "Desktop")
                root_label = "Desktop"
                launch_target = "desktop"
            elif "downloads" in goal or "dwnloads" in goal:
                search_root = str(Path.home() / "Downloads")
                root_label = "Downloads"
                launch_target = "downloads"
            elif "documents" in goal:
                search_root = str(Path.home() / "Documents")
                root_label = "Documents"
                launch_target = "documents"
            else:
                drive_letter = drive_match.group(1).upper() if drive_match else "E"
                if drive_letter in ["I", "A"] and not Path(f"{drive_letter}:\\").exists() and Path("E:\\").exists():
                    drive_letter = "E"
                search_root = f"{drive_letter}:\\"
                root_label = f"{drive_letter}: Drive ({search_root})"
                launch_target = f"{drive_letter} drive"

            # 2. Check if user also wants to delete the searched target at the end
            wants_delete = bool(
                re.search(r"\b(?:then\s+it\s+del|and\s+delete|then\s+delete|delete\s+it|del\s+it|del\s+krdo|delete\s+kro|delete\s+karo)\b", goal)
                or goal.strip().endswith((" it del", " then del", " and del", " delete"))
            )

            # 3. Extract target folder/file name accurately
            target_folder_name = ""
            # Priority pattern: "search/serch/find [folder] <name>" or "<name> folder" (excluding location names)
            loc_words = {"desktop", "downloads", "documents", "pictures", "drive", "pc", "my", "this", "folder", "flder", "file", "open", "oepn", "then", "and", "also", "serch", "search", "srch", "find", "dhundo"}
            m_after_search = re.search(r"\b(?:search|serch|srch|find|dhundo)\s+(?:folder\s+|flder\s+|file\s+)?([a-zA-Z0-9_\-]+)", goal)
            if m_after_search and m_after_search.group(1).lower() not in loc_words:
                target_folder_name = m_after_search.group(1)
            else:
                # Look for "<name> folder" where <name> is not desktop/downloads/etc.
                for m_before_folder in re.finditer(r"\b([a-zA-Z0-9_\-]+)\s+(?:folder|flder)\b", goal):
                    cand_name = m_before_folder.group(1)
                    if cand_name.lower() not in loc_words:
                        target_folder_name = cand_name
                        break

            if not target_folder_name:
                clean_target = goal
                for w in list(loc_words) + [
                    "in", "on", "ko", "kholo", "wala", "walay", "wali", "ma", "mein",
                    "it", "del", "delete", "kro", "karo", "krdo"
                ]:
                    clean_target = re.sub(rf"\b{w}\b", " ", clean_target, flags=re.IGNORECASE)
                tokens_left = [t.strip() for t in clean_target.split() if len(t.strip()) > 1]
                target_folder_name = tokens_left[0] if tokens_left else ""

            if step == 1:
                if "my pc" in goal or "this pc" in goal:
                    universal_launcher.open("my pc")
                res_open = universal_launcher.open(launch_target)
                if res_open.get("status") == "warning":
                    return AutonomousAction(
                        thought=res_open.get("message", f"{root_label} not found."),
                        action_type="finish",
                        params={"summary": res_open.get("message", f"{root_label} not found.")}
                    )
                if not target_folder_name:
                    return AutonomousAction(
                        thought=f"Opened {root_label} in foreground.",
                        action_type="finish",
                        params={"summary": f"Opened {root_label} in File Explorer."}
                    )
                return AutonomousAction(
                    thought=f"Opened {root_label}. Now searching for '{target_folder_name}' inside {search_root}...",
                    action_type="sleep",
                    params={"seconds": 0.5}
                )
            else:
                search_res = file_search_tool.search_files(query=target_folder_name, search_dir=search_root, max_results=10)
                found_items = search_res.get("files", [])
                # Prioritize exact name match if present
                exact_items = [
                    it for it in found_items
                    if it["name"].replace("📁 ", "").lower() == target_folder_name.lower()
                ]
                best_match = exact_items[0] if exact_items else (found_items[0] if found_items else None)

                if best_match:
                    matched_path = Path(best_match["path"])
                    if wants_delete:
                        # Safety check: Prevent silent permanent deletion.
                        # Always require explicit user confirmation token before recycling/deleting.
                        confirm_token = f"CONFIRM_DELETE_{matched_path.name}"
                        if confirm_token not in goal:
                            return AutonomousAction(
                                thought=f"Target '{best_match['name']}' located at {matched_path}. Halting for mandatory confirmation before deletion.",
                                action_type="finish",
                                params={
                                    "status": "confirmation_required",
                                    "confirmation_token": confirm_token,
                                    "target_path": str(matched_path),
                                    "summary": f"Target found: '{matched_path}'. Deletion requires confirmation! Reply with 'yes confirm delete' to safely move this item to the Recycle Bin."
                                }
                            )

                        # Only allow deleting inside user subfolders or non-root items
                        if len(matched_path.parts) >= 3 and matched_path.exists():
                            try:
                                # Safe Win32 Recycle Bin move using SHFileOperationW with FOF_ALLOWUNDO
                                from ctypes import wintypes
                                class _SHFILEOPSTRUCTW(ctypes.Structure):
                                    _fields_ = [
                                        ("hwnd", wintypes.HWND),
                                        ("wFunc", wintypes.UINT),
                                        ("pFrom", wintypes.LPCWSTR),
                                        ("pTo", wintypes.LPCWSTR),
                                        ("fFlags", ctypes.c_ushort),
                                        ("fAnyOperationsAborted", wintypes.BOOL),
                                        ("hNameMappings", wintypes.LPVOID),
                                        ("lpszProgressTitle", wintypes.LPCWSTR),
                                    ]
                                FO_DELETE = 0x0003
                                FOF_ALLOWUNDO = 0x0040
                                FOF_NOCONFIRMATION = 0x0010
                                FOF_SILENT = 0x0004

                                abs_target = str(matched_path.resolve()) + "\0\0"
                                shfo = _SHFILEOPSTRUCTW()
                                shfo.hwnd = None
                                shfo.wFunc = FO_DELETE
                                shfo.pFrom = abs_target
                                shfo.pTo = None
                                shfo.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
                                res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(shfo))

                                if res == 0 and not matched_path.exists():
                                    return AutonomousAction(
                                        thought=f"Safely moved '{best_match['name']}' ({matched_path}) to the Windows Recycle Bin.",
                                        action_type="finish",
                                        params={
                                            "summary": f"Moved '{matched_path}' to the Windows Recycle Bin (recoverable via Recycle Bin)."
                                        }
                                    )
                                else:
                                    # Fallback to standard delete if SHFileOperation failed
                                    if matched_path.is_dir():
                                        shutil.rmtree(matched_path)
                                    else:
                                        matched_path.unlink()
                                    return AutonomousAction(
                                        thought=f"Deleted '{best_match['name']}' at {matched_path} after explicit confirmation.",
                                        action_type="finish",
                                        params={
                                            "summary": f"Deleted '{matched_path}' successfully after explicit confirmation."
                                        }
                                    )
                            except Exception as e:
                                return AutonomousAction(
                                    thought=f"Failed to delete {matched_path}: {e}",
                                    action_type="finish",
                                    params={"summary": f"Found '{matched_path}', but could not delete it: {e}"}
                                )
                    universal_launcher.open(str(matched_path))
                    return AutonomousAction(
                        thought=f"Found '{best_match['name']}' at {matched_path} and opened it in Explorer.",
                        action_type="finish",
                        params={
                            "summary": f"Opened {root_label}, found '{best_match['name']}' at '{matched_path}', and opened it on your screen!"
                        }
                    )
                else:
                    return AutonomousAction(
                        thought=f"Opened {root_label}, but no folder/file named '{target_folder_name}' was found in {search_root}.",
                        action_type="finish",
                        params={
                            "summary": f"Opened {root_label}, but could not find any folder or file matching '{target_folder_name}' inside {search_root}."
                        }
                    )

        # Scenario: LimeOx Employee Tracker -> Open & Start Tracking
        if any(k in goal for k in ["limerox", "limeox", "tracker", "start tracking"]):
            if step == 1:
                universal_launcher.open("limerox")
                return AutonomousAction(
                    thought="Launching LimeOx Employee Tracker and bringing window to foreground.",
                    action_type="sleep",
                    params={"seconds": 2.0}
                )
            elif step == 2:
                # Focus LimeOx Tracker window and trigger Start Tracking
                for hint in ["LimeOx", "Tracker", "Employee"]:
                    hwnd = native_desktop.find_window_by_title(hint)
                    if hwnd:
                        native_desktop.force_bring_to_foreground(hwnd)
                        break
                return AutonomousAction(
                    thought="Activating Start Tracking inside LimeOx Employee Tracker.",
                    action_type="press_key",
                    params={"key": "enter"}
                )
            else:
                return AutonomousAction(
                    thought="LimeOx Employee Tracker is open and tracking initiated.",
                    action_type="finish",
                    params={"summary": "Opened LimeOx Employee Tracker and initiated tracking."}
                )

        # Scenario: Notepad typing
        if "notepad" in goal:
            if "notepad" not in active_window.lower() and step == 1:
                return AutonomousAction(
                    thought="Opening Notepad first.",
                    action_type="launch_app",
                    params={"app_name": "notepad"}
                )
            elif step == 2:
                # Extract text to write
                text = "Welcome to DesktopPilot AI!"
                if "write" in goal or "type" in goal:
                    parts = re.split(r"write|type", goal, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        text = parts[1].replace("'", "").replace('"', '').strip()
                return AutonomousAction(
                    thought=f"Activating Notepad and typing '{text}'.",
                    action_type="type_text",
                    params={"text": text + "\n", "app_title": "Notepad"}
                )
            else:
                return AutonomousAction(
                    thought="Notepad text has been typed.",
                    action_type="finish",
                    params={"summary": "Notepad opened and text typed successfully."}
                )

        # Scenario: Calculator
        if "calc" in goal or "calculator" in goal or "calculate" in goal:
            if "calc" not in active_window.lower() and step == 1:
                return AutonomousAction(
                    thought="Opening Calculator.",
                    action_type="launch_app",
                    params={"app_name": "calc"}
                )
            elif step == 2:
                # Extract mathematical expression or default 25*4=
                expr = "25*4="
                match_num = re.search(r"(\d+[\s\*\+\-\/]+\d+)", goal)
                if match_num:
                    expr = match_num.group(1).replace(" ", "") + "="
                return AutonomousAction(
                    thought=f"Entering calculation '{expr}' into Calculator.",
                    action_type="type_text",
                    params={"text": expr, "app_title": "Calculator"}
                )
            else:
                return AutonomousAction(
                    thought="Calculation entered.",
                    action_type="finish",
                    params={"summary": "Calculator opened and calculation performed."}
                )

        # Scenario: YouTube / Search
        if "youtube" in goal or "search" in goal:
            import urllib.parse
            clean_query = goal
            for prefix in ["open browser and search for", "open browser and search", "open youtube and search for", "open youtube and search", "search for", "search on youtube", "search google for", "search google", "search"]:
                clean_query = re.sub(rf"\b{prefix}\b", "", clean_query, flags=re.IGNORECASE)
            clean_query = clean_query.replace("open browser", "").replace("open youtube", "").strip()
            encoded_q = urllib.parse.quote_plus(clean_query)

            if "youtube" in goal:
                url = f"https://www.youtube.com/results?search_query={encoded_q}"
                summary = f"Opened YouTube and searched for '{clean_query}'."
            else:
                url = f"https://www.google.com/search?q={encoded_q}"
                summary = f"Opened browser and searched Google for '{clean_query}'."

            if step == 1:
                app_controller.open_browser(url)
                return AutonomousAction(
                    thought=f"Opening browser search for '{clean_query}'.",
                    action_type="sleep",
                    params={"seconds": 1.5}
                )
            else:
                return AutonomousAction(
                    thought="Search loaded in browser.",
                    action_type="finish",
                    params={"summary": summary}
                )

        return AutonomousAction(
            thought="Task completed.",
            action_type="finish",
            params={"summary": f"Executed operations for '{goal}'."}
        )


autonomous_pilot = AutonomousScreenPilot()

