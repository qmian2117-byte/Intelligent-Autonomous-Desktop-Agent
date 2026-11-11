"""
File Management & Disk Space Analyzer Tool for DesktopPilot AI.
Includes deep folder scanning, large file detection, temporary file auditing,
and a mandatory two-phase Safety Confirmation System for deletions.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from utils.logger import logger


class FileInfo(BaseModel):
    path: str
    size_bytes: int
    size_readable: str
    last_modified: str
    category: str


class DiskAnalysisReport(BaseModel):
    target_path: str
    total_scanned_files: int
    total_size_bytes: int
    total_size_readable: str
    large_files: List[FileInfo]
    temp_files: List[FileInfo]
    estimated_reclaimable_space: str
    safety_confirmation_token: Optional[str] = None
    warning_notice: str


class SafeFileManagerTool:
    """
    Analyzes disk usage and manages safe cleanup.
    Guarantees user files (Documents, Desktop, Code) are NEVER deleted automatically.
    """

    # Protected paths that should NEVER be purged
    PROTECTED_DIRECTORIES = [
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
    ]

    # File extensions recognized as temporary / cache
    TEMP_EXTENSIONS = {".tmp", ".temp", ".log", ".bak", ".old", ".dmp", ".chk", ".crdownload"}

    def __init__(self):
        # Pending deletion registry: token -> list of absolute paths
        self._pending_deletions: Dict[str, List[Path]] = {}

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Converts bytes to human readable string (KB, MB, GB)."""
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:3.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def analyze_storage(
        self,
        target_dir: str,
        large_file_threshold_mb: int = 100,
        max_results: int = 15
    ) -> DiskAnalysisReport:
        """
        Scans a directory or drive to find storage hogs and safe temporary cleanup candidates.
        DOES NOT DELETE ANYTHING.
        """
        root_path = Path(target_dir).resolve()
        if not root_path.exists():
            return DiskAnalysisReport(
                target_path=target_dir,
                total_scanned_files=0,
                total_size_bytes=0,
                total_size_readable="0 B",
                large_files=[],
                temp_files=[],
                estimated_reclaimable_space="0 B",
                warning_notice=f"Path '{target_dir}' does not exist."
            )

        threshold_bytes = large_file_threshold_mb * 1024 * 1024
        total_size = 0
        file_count = 0
        large_files: List[FileInfo] = []
        temp_files: List[FileInfo] = []
        temp_reclaimable_bytes = 0
        purge_candidate_paths: List[Path] = []

        try:
            for entry in os.scandir(root_path):
                try:
                    if entry.is_file(follow_symlinks=False):
                        stat = entry.stat()
                        size = stat.st_size
                        total_size += size
                        file_count += 1
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                        ext = Path(entry.name).suffix.lower()
                        readable = self._format_size(size)

                        # Detect large files
                        if size >= threshold_bytes:
                            large_files.append(
                                FileInfo(
                                    path=entry.path,
                                    size_bytes=size,
                                    size_readable=readable,
                                    last_modified=mtime,
                                    category="Large File"
                                )
                            )

                        # Detect temporary / junk files
                        if ext in self.TEMP_EXTENSIONS or "cache" in entry.name.lower() or entry.name.startswith("~"):
                            temp_files.append(
                                FileInfo(
                                    path=entry.path,
                                    size_bytes=size,
                                    size_readable=readable,
                                    last_modified=mtime,
                                    category="Temporary / Cache"
                                )
                            )
                            temp_reclaimable_bytes += size
                            purge_candidate_paths.append(Path(entry.path))

                    elif entry.is_dir(follow_symlinks=False):
                        # Detect standard temp directory folders
                        if entry.name.lower() in ["temp", "tmp", "caches", "crashreports"]:
                            dir_size = sum(f.stat().st_size for f in Path(entry.path).rglob('*') if f.is_file())
                            total_size += dir_size
                            temp_reclaimable_bytes += dir_size
                            temp_files.append(
                                FileInfo(
                                    path=entry.path,
                                    size_bytes=dir_size,
                                    size_readable=self._format_size(dir_size),
                                    last_modified="",
                                    category="Temp Directory"
                                )
                            )
                            purge_candidate_paths.append(Path(entry.path))
                except (PermissionError, FileNotFoundError):
                    continue
        except Exception as e:
            logger.warning(f"Error scanning directory '{root_path}': {e}")

        # Sort large files descending
        large_files.sort(key=lambda x: x.size_bytes, reverse=True)
        large_files = large_files[:max_results]

        # Generate unique safety confirmation token for this analysis session
        token = None
        if purge_candidate_paths:
            token = f"CONFIRM-CLEANUP-{uuid.uuid4().hex[:8].upper()}"
            self._pending_deletions[token] = purge_candidate_paths

        return DiskAnalysisReport(
            target_path=str(root_path),
            total_scanned_files=file_count,
            total_size_bytes=total_size,
            total_size_readable=self._format_size(total_size),
            large_files=large_files,
            temp_files=temp_files[:max_results],
            estimated_reclaimable_space=self._format_size(temp_reclaimable_bytes),
            safety_confirmation_token=token,
            warning_notice="ANALYSIS ONLY. No files were removed. To delete safe temporary files, user must explicitly approve using the safety token."
        )

    def execute_confirmed_cleanup(self, confirmation_token: str, user_explicit_approval: bool) -> Dict[str, Any]:
        """
        Executes deletion ONLY when provided with a valid token and explicit boolean confirmation.
        """
        if not user_explicit_approval:
            return {
                "status": "aborted",
                "message": "User did not grant approval. Cleanup cancelled."
            }

        if confirmation_token not in self._pending_deletions:
            return {
                "status": "invalid_token",
                "message": "Security Error: Confirmation token expired or invalid."
            }

        targets = self._pending_deletions.pop(confirmation_token)
        deleted_count = 0
        reclaimed_bytes = 0
        failed_deletions = []

        for target in targets:
            # Enforce protection policy
            is_protected = any(str(target).startswith(p) for p in self.PROTECTED_DIRECTORIES)
            if is_protected:
                failed_deletions.append(f"Protected path blocked: {target}")
                continue

            try:
                if target.is_file():
                    size = target.stat().st_size
                    target.unlink()
                    deleted_count += 1
                    reclaimed_bytes += size
                elif target.is_dir():
                    shutil.rmtree(target)
                    deleted_count += 1
            except Exception as e:
                failed_deletions.append(f"{target.name}: {str(e)}")

        return {
            "status": "success",
            "deleted_items": deleted_count,
            "reclaimed_space": self._format_size(reclaimed_bytes),
            "errors": failed_deletions
        }


# Global file manager instance
file_manager_tool = SafeFileManagerTool()
