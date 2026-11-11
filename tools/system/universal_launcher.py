"""
Universal "Open Anything" Tool for DesktopPilot AI.
Launches any application, web service, special folder, drive, or file via natural language.
Forces newly opened File Explorer and application windows to the foreground above the browser.
"""

import os
import time
import subprocess
import webbrowser
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List
from tools.desktop.native_input import native_desktop
from utils.logger import logger


class UniversalLauncher:
    """Intelligent target resolver and foreground launcher for Windows."""

    # Well-known Windows shell folders and their actual disk paths
    REAL_FOLDERS = {
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "desktop": Path.home() / "Desktop",
        "pictures": Path.home() / "Pictures",
        "images": Path.home() / "Pictures",
        "photos": Path.home() / "Pictures",
        "videos": Path.home() / "Videos",
        "music": Path.home() / "Music",
    }

    # Common web services and their direct URLs
    POPULAR_WEBSITES = {
        "chatgpt": "https://chatgpt.com",
        "openai": "https://chatgpt.com",
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "linkedin": "https://www.linkedin.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "reddit": "https://www.reddit.com",
        "whatsapp": "https://web.whatsapp.com",
        "netflix": "https://www.netflix.com",
        "spotify web": "https://open.spotify.com",
        "slack web": "https://app.slack.com",
    }

    # Known standard executable aliases
    APP_ALIASES = {
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "excel": "excel.exe",
        "word": "winword.exe",
        "powerpoint": "powerpnt.exe",
        "spotify": "spotify.exe",
        "vlc": "vlc.exe",
        "discord": "discord.exe",
    }

    def _open_explorer_foreground(self, path_arg: str, title_hints: List[str]):
        """
        Forces Windows Explorer to open a brand-new window (/n,) and brings it to HWND_TOPMOST
        so it never stays hidden behind Chrome.
        """
        try:
            subprocess.Popen(["explorer.exe", "/n,", path_arg])
        except Exception:
            try:
                os.startfile(path_arg)
            except Exception as e:
                logger.error(f"Explorer launch failed for {path_arg}: {e}")
                return

        # Wait briefly for Explorer window creation, then force to foreground
        time.sleep(0.55)
        for hint in title_hints:
            hwnd = native_desktop.find_window_by_title(hint)
            if hwnd:
                native_desktop.force_bring_to_foreground(hwnd)
                break

    def _find_tracker_executable(self) -> Optional[Path]:
        """Locates LimeOxEmployeeTracker.exe on the user's PC."""
        candidates = [
            Path.home() / "Downloads" / "LimeOxEmployeeTracker.exe",
            Path.home() / "Downloads" / "LimeOxEmployeeTracker (1).exe",
            Path.home() / "Desktop" / "LimeOxEmployeeTracker.exe",
        ]
        for c in candidates:
            if c.exists():
                return c

        # Fallback search in Downloads & Desktop for any *LimeOx* or *Tracker*.exe
        for folder in [Path.home() / "Downloads", Path.home() / "Desktop"]:
            if folder.exists():
                for exe in folder.glob("*.exe"):
                    if any(k in exe.name.lower() for k in ["lime", "tracker", "time"]):
                        return exe
        return None

    def _find_slack_executable(self) -> Optional[Path]:
        """Locates Slack desktop executable if installed."""
        local_app = Path(os.environ.get("LOCALAPPDATA", ""))
        candidates = [
            local_app / "slack" / "slack.exe",
            local_app / "Programs" / "slack" / "Slack.exe",
            Path.home() / "Desktop" / "Slack.lnk",
        ]
        for c in candidates:
            if c.exists():
                return c
        lnk = self._find_start_menu_shortcut("slack")
        return lnk

    def _find_start_menu_shortcut(self, target_name: str) -> Optional[Path]:
        """Scans Desktop and Windows Start Menu directories for .lnk shortcuts matching target."""
        search_roots = [
            Path.home() / "Desktop",
            Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]
        target_clean = target_name.lower().replace(" ", "").replace("-", "")

        for root in search_roots:
            if not root.exists():
                continue
            for lnk in root.rglob("*.lnk"):
                lnk_clean = lnk.stem.lower().replace(" ", "").replace("-", "")
                if target_clean in lnk_clean:
                    return lnk
        return None

    def open(self, target: str) -> Dict[str, Any]:
        """
        Universal launcher: Resolves and opens apps, websites, drives, folders, or files in the foreground.
        """
        target_str = target.strip().rstrip(".?!")
        lower = target_str.lower()

        # 1. LimeOx Employee Tracker ("limerox", "limeox", "tracker", "employee tracker")
        if any(k in lower for k in ["limerox", "limeox", "tracker", "time tracker", "employee tracker"]):
            tracker_exe = self._find_tracker_executable()
            if tracker_exe:
                try:
                    os.startfile(str(tracker_exe))
                    time.sleep(0.8)
                    for hint in ["LimeOx", "Tracker", "Employee"]:
                        hwnd = native_desktop.find_window_by_title(hint)
                        if hwnd:
                            native_desktop.force_bring_to_foreground(hwnd)
                            break
                    return {
                        "status": "success",
                        "category": "app",
                        "target": str(tracker_exe),
                        "message": f"Launched LimeOx Employee Tracker ({tracker_exe.name})."
                    }
                except Exception as e:
                    return {"status": "error", "message": f"Failed to launch LimeOx Tracker: {e}"}

        # 2. Slack ("slack", "open slack")
        if "slack" in lower:
            slack_exe = self._find_slack_executable()
            if slack_exe:
                try:
                    os.startfile(str(slack_exe))
                    time.sleep(0.6)
                    hwnd = native_desktop.find_window_by_title("Slack")
                    if hwnd:
                        native_desktop.force_bring_to_foreground(hwnd)
                    return {
                        "status": "success",
                        "category": "app",
                        "target": str(slack_exe),
                        "message": "Launched Slack desktop app."
                    }
                except Exception:
                    pass
            # Fallback to Slack Web in new browser window
            webbrowser.open_new("https://app.slack.com")
            return {
                "status": "success",
                "category": "website",
                "target": "https://app.slack.com",
                "message": "Opened Slack in browser (https://app.slack.com)."
            }

        # 3. Any Drive Letter A-Z (e.g. "c drive", "d drive", "e drive", "f drive", "e:", "f:")
        # Includes phonetic Speech-to-Text corrections ('i drive' / 'a drive' / 'dai' -> 'E:\' when I:/A: don't exist)
        import re
        drive_match = re.search(r"\b([a-z])\s*drive\b|^([a-z]):\\?$", lower)
        if drive_match or lower in ["c", "d", "e", "f", "g"] or "dai" in lower:
            letter = (drive_match.group(1) or drive_match.group(2) if drive_match else ("e" if "dai" in lower else lower)).upper()
            # Phonetic STT fallback: Urdu/English accent "E drive" is often transcribed as "I drive" or "A drive"
            if letter in ["I", "A"] and not Path(f"{letter}:\\").exists() and Path("E:\\").exists():
                letter = "E"
            drive_root = f"{letter}:\\"
            if Path(drive_root).exists():
                self._open_explorer_foreground(drive_root, [f"({letter}:)", drive_root, "New Volume", "Local Disk", "File Explorer"])
                return {
                    "status": "success",
                    "category": "drive",
                    "target": drive_root,
                    "message": f"Opened {letter}: Drive ({drive_root}) in foreground."
                }
            else:
                available = [f"{chr(c)}:\\" for c in range(ord('C'), ord('Z') + 1) if Path(f"{chr(c)}:\\").exists()]
                avail_str = ", ".join(available) if available else "C:\\"
                return {
                    "status": "warning",
                    "category": "drive_not_found",
                    "target": drive_root,
                    "message": f"Drive {letter}:\\ is not connected on this PC. Available drives on your PC: {avail_str}"
                }

        # 4. This PC / My Computer
        if any(k in lower for k in ["this pc", "my pc", "my computer", "open pc"]) or lower == "pc":
            self._open_explorer_foreground("::{20D04FE0-3AEA-1069-A2D8-08002B30309D}", ["This PC", "File Explorer"])
            return {"status": "success", "category": "system_folder", "target": "This PC", "message": "Opened This PC in foreground."}

        # 5. Windows Special Shell Folders (Downloads, Documents, Desktop, etc. - tolerant to Roman Urdu & typos)
        tokens_in_target = [t for t in re.findall(r"\w+", lower) if len(t) >= 4 and t not in ["folder", "flder", "wala", "walay", "open", "kholo"]]
        for folder_key, folder_path in self.REAL_FOLDERS.items():
            is_match = (
                lower == folder_key
                or folder_key in lower
                or (len(lower) >= 4 and difflib.SequenceMatcher(None, lower, folder_key).ratio() >= 0.76)
                or any(difflib.SequenceMatcher(None, tok, folder_key).ratio() >= 0.76 for tok in tokens_in_target)
            )
            if is_match and folder_path.exists():
                self._open_explorer_foreground(str(folder_path), [folder_key.title(), "File Explorer"])
                return {"status": "success", "category": "folder", "target": folder_key, "message": f"Opened {folder_key.title()} folder in foreground."}

        # 6. Direct File / Directory Path
        potential_path = Path(target_str)
        if potential_path.exists():
            try:
                if potential_path.is_dir():
                    self._open_explorer_foreground(str(potential_path.resolve()), [potential_path.name, "File Explorer"])
                else:
                    os.startfile(str(potential_path.resolve()))
                return {"status": "success", "category": "path", "target": str(potential_path), "message": f"Opened '{potential_path.name}'."}
            except Exception as e:
                return {"status": "error", "message": f"Failed to open path: {e}"}

        # 7. Web URLs or Popular Web Services
        for site_key, site_url in self.POPULAR_WEBSITES.items():
            if lower == site_key or (len(lower) >= 4 and difflib.SequenceMatcher(None, lower, site_key).ratio() >= 0.82):
                webbrowser.open_new(site_url)
                return {"status": "success", "category": "website", "target": site_url, "message": f"Opened {site_key.title()} ({site_url})."}

        if lower.startswith("http://") or lower.startswith("https://") or lower.endswith(".com") or lower.endswith(".org") or lower.endswith(".io"):
            url = target_str if target_str.startswith("http") else f"https://{target_str}"
            webbrowser.open_new(url)
            return {"status": "success", "category": "website", "target": url, "message": f"Opened website: {url}"}

        # 8. Direct App Aliases (with typo tolerance)
        for alias, exe_cmd in self.APP_ALIASES.items():
            if lower == alias or lower == f"{alias} app" or (len(lower) >= 4 and difflib.SequenceMatcher(None, lower, alias).ratio() >= 0.82):
                try:
                    os.startfile(exe_cmd)
                    time.sleep(0.5)
                    hwnd = native_desktop.find_window_by_title(alias.title())
                    if hwnd:
                        native_desktop.force_bring_to_foreground(hwnd)
                    return {"status": "success", "category": "app", "target": exe_cmd, "message": f"Launched '{alias.title()}'."}
                except Exception:
                    try:
                        subprocess.Popen(["cmd.exe", "/c", "start", "", exe_cmd], shell=False)
                        return {"status": "success", "category": "app", "target": exe_cmd, "message": f"Launched '{alias.title()}'."}
                    except Exception as sub_err:
                        return {"status": "error", "message": f"Could not launch '{alias}': {sub_err}"}

        # 9. Windows Start Menu / Desktop Shortcut Search
        lnk_file = self._find_start_menu_shortcut(target_str)
        if lnk_file:
            try:
                os.startfile(str(lnk_file))
                time.sleep(0.5)
                hwnd = native_desktop.find_window_by_title(lnk_file.stem)
                if hwnd:
                    native_desktop.force_bring_to_foreground(hwnd)
                return {"status": "success", "category": "start_menu_shortcut", "target": lnk_file.name, "message": f"Launched '{lnk_file.stem}'."}
            except Exception as e:
                logger.warning(f"Failed to launch shortcut {lnk_file}: {e}")

        # 10. Fallback: Safe Shell start
        try:
            os.startfile(target_str)
            return {"status": "success", "category": "shell_start", "target": target_str, "message": f"Launched '{target_str}'."}
        except Exception:
            # Reject dangerous characters in raw shell fallback
            if any(ch in target_str for ch in ["&", "|", ";", "`", "$", "<", ">", "\n", "\r"]):
                return {"status": "error", "message": f"Refused to launch target containing illegal shell characters: '{target_str}'"}
            try:
                subprocess.Popen(["cmd.exe", "/c", "start", "", target_str], shell=False)
                return {"status": "success", "category": "shell_start", "target": target_str, "message": f"Sent launch command for '{target_str}'."}
            except Exception as e:
                return {"status": "error", "message": f"Failed to launch '{target_str}': {e}"}


universal_launcher = UniversalLauncher()
