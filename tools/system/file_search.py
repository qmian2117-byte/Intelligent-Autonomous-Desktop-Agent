"""
File & Folder Search Tool for DesktopPilot AI.
Provides fast computer-wide file and folder discovery across C:, D:, E:, user folders,
previews, path copying, and Explorer reveal.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import logger


class WindowsFileSearchTool:
    """Intelligent Desktop File & Folder Search Engine."""

    def __init__(self):
        user_home = Path.home()
        self.default_search_roots = [
            Path("E:\\"),
            Path("D:\\"),
            user_home / "Desktop",
            user_home / "Documents",
            user_home / "Downloads",
            user_home / "Pictures",
            Path.cwd(),
        ]

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:3.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def search_files(
        self,
        query: str,
        search_dir: Optional[str] = None,
        extension: Optional[str] = None,
        max_results: int = 15
    ) -> Dict[str, Any]:
        """
        Searches for both folders and files by name, pattern, or extension across drives.
        Automatically extracts drive hints like 'fyp in e drive' -> query='fyp', search_dir='E:\\'.
        """
        raw_q = query.lower().strip()

        # Extract drive hint if embedded inside query (e.g. "fyp in e drive", "e drive ma aiml")
        drive_match = re.search(r"\b(?:in|on|from|ma|mein)?\s*([a-z])\s*drive\b|\b([a-z]):", raw_q)
        if drive_match and not search_dir:
            drive_letter = (drive_match.group(1) or drive_match.group(2)).upper()
            candidate_drive = f"{drive_letter}:\\"
            if Path(candidate_drive).exists():
                search_dir = candidate_drive
            raw_q = re.sub(r"\b(?:in|on|from|ma|mein)?\s*[a-z]\s*drive\b|\b[a-z]:", "", raw_q).strip()

        # Remove English & Roman Urdu filler words
        for filler in [
            "folders", "folder", "flder", "files", "file", "search", "serch", "srch",
            "find", "dhundo", "dhoondo", "khojo", "wala", "walay", "wali", "ma", "mein",
            "in", "on", "my", "pc", "ko", "ka", "ki", "ke"
        ]:
            raw_q = re.sub(rf"\b{filler}\b", "", raw_q).strip()

        query_clean = raw_q.strip()
        ext_clean = extension.lower().strip() if extension else ""
        if ext_clean and not ext_clean.startswith("."):
            ext_clean = f".{ext_clean}"

        # Determine target search roots
        roots_to_scan: List[Path] = []
        if search_dir and Path(search_dir).exists():
            roots_to_scan.append(Path(search_dir))
        else:
            roots_to_scan = [p for p in self.default_search_roots if p.exists()]

        results: List[Dict[str, Any]] = []
        seen_paths = set()

        for root in roots_to_scan:
            try:
                root_depth = len(root.resolve().parts)
                for current_root, dirs, files in os.walk(root):
                    curr_path = Path(current_root)
                    # Limit depth to 4 levels so large drives scan in < 0.8s
                    if len(curr_path.parts) - root_depth > 4:
                        dirs[:] = []
                        continue

                    # Skip hidden/system/heavy dirs
                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".")
                        and d not in ["node_modules", "AppData", "__pycache__", "$RECYCLE.BIN", "System Volume Information", "Windows", "venv", ".venv"]
                    ]

                    # 1. Match Folders (Directories) first!
                    if not ext_clean:
                        for d in dirs:
                            if not query_clean or query_clean in d.lower():
                                folder_path = curr_path / d
                                resolved_str = str(folder_path.resolve())
                                if resolved_str in seen_paths:
                                    continue
                                seen_paths.add(resolved_str)
                                try:
                                    stat = folder_path.stat()
                                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                                except Exception:
                                    mod_time = ""
                                results.append({
                                    "name": f"📁 {d}",
                                    "path": resolved_str,
                                    "size": "Folder",
                                    "modified": mod_time,
                                    "is_directory": True
                                })
                                if len(results) >= max_results:
                                    break

                    if len(results) >= max_results:
                        break

                    # 2. Match Files
                    for f in files:
                        f_lower = f.lower()
                        if ext_clean and not f_lower.endswith(ext_clean):
                            continue
                        if query_clean and (query_clean not in f_lower):
                            continue

                        file_path = curr_path / f
                        resolved_str = str(file_path.resolve())
                        if resolved_str in seen_paths:
                            continue
                        seen_paths.add(resolved_str)
                        try:
                            stat = file_path.stat()
                            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            results.append({
                                "name": f,
                                "path": resolved_str,
                                "size": self._format_size(stat.st_size),
                                "modified": mod_time,
                                "is_directory": False
                            })
                            if len(results) >= max_results:
                                break
                        except Exception:
                            continue

                    if len(results) >= max_results:
                        break
            except Exception as e:
                logger.warning(f"Error scanning directory '{root}': {e}")

        logger.info(f"File/Folder search for '{query_clean}' (dir={search_dir}) returned {len(results)} items.")
        return {
            "status": "success",
            "query": query_clean or query,
            "search_dir": search_dir or "All Drives",
            "total_found": len(results),
            "files": results
        }

    def inspect_directory_contents(self, target_dir: str = "E:\\") -> Dict[str, Any]:
        """
        Counts and lists all top-level folders and files inside a drive or directory.
        Answers questions like 'E drive mein kitne folder hain' or 'how many folders in E drive'.
        """
        p = Path(target_dir)
        if not p.exists():
            return {"status": "error", "message": f"Directory '{target_dir}' does not exist."}

        folders = []
        files = []
        try:
            for item in p.iterdir():
                if item.name.startswith("$") or item.name in ["System Volume Information", "__pycache__"]:
                    continue
                if item.is_dir():
                    folders.append(item.name)
                else:
                    files.append(item.name)
        except Exception as e:
            return {"status": "error", "message": str(e)}

        folder_list_str = ", ".join(folders[:15])
        return {
            "status": "success",
            "directory": str(p),
            "folder_count": len(folders),
            "file_count": len(files),
            "folders": folders,
            "files": files,
            "message": (
                f"In {str(p)}, there are {len(folders)} folders and {len(files)} files.\n"
                f"📁 Folders ({len(folders)}): {folder_list_str}"
            )
        }

    def preview_file(self, file_path: str, max_lines: int = 15) -> Dict[str, Any]:
        """Reads and returns a preview of the file (first N lines for text, or file metadata)."""
        p = Path(file_path).resolve()
        if not p.exists():
            return {"status": "error", "message": f"File '{file_path}' does not exist."}

        text_exts = {".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".csv", ".html", ".css", ".log", ".yaml", ".yml", ".ini"}
        if p.suffix.lower() in text_exts:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
                return {
                    "status": "success",
                    "file_name": p.name,
                    "path": str(p),
                    "type": "text",
                    "preview": content
                }
            except Exception as e:
                return {"status": "error", "message": f"Could not read file: {e}"}
        else:
            stat = p.stat()
            return {
                "status": "success",
                "file_name": p.name,
                "path": str(p),
                "type": "binary/media",
                "size": self._format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            }

    def copy_path_to_clipboard(self, file_path: str) -> Dict[str, Any]:
        """Copies the given file path directly to the Windows clipboard."""
        from tools.system.clipboard_ai import clipboard_ai
        p = Path(file_path).resolve()
        path_str = str(p)
        clipboard_ai.set_clipboard_text(path_str)
        return {"status": "success", "message": f"Copied path to clipboard: {path_str}"}

    def reveal_in_explorer(self, file_path: str) -> Dict[str, Any]:
        """Opens Windows Explorer and highlights the specified file."""
        p = Path(file_path).resolve()
        if not p.exists():
            return {"status": "error", "message": f"File '{file_path}' does not exist."}
        try:
            subprocess.Popen(["explorer.exe", f"/select,{str(p)}"], shell=False)
            return {"status": "success", "message": f"Revealed '{p.name}' in File Explorer."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


file_search_tool = WindowsFileSearchTool()
