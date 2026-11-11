"""
Smart File Management Tool for DesktopPilot AI.
Provides safe, automated file system operations:
- Copy, Move, Batch Rename
- Compress to ZIP & Extract from ZIP
- Auto-organize directory by file types (Documents, Images, Code, Videos, Archives)
- Two-phase safety check for deletions
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import logger


class SmartFileManager:
    """Intelligent File Organizer & Manipulator."""

    # Categorization mapping for auto-organization
    CATEGORIES = {
        "Documents": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".epub"},
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"},
        "Videos": {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"},
        "Audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"},
        "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
        "Code": {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".cpp", ".c", ".java"}
    }

    def copy_item(self, source: str, destination: str) -> Dict[str, Any]:
        """Copies a file or entire directory to the target destination."""
        src_path = Path(source).resolve()
        dst_path = Path(destination).resolve()

        if not src_path.exists():
            return {"status": "error", "message": f"Source '{source}' does not exist."}

        try:
            if src_path.is_file():
                if dst_path.is_dir():
                    dst_path = dst_path / src_path.name
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            logger.info(f"Copied '{src_path.name}' to '{dst_path}'.")
            return {"status": "success", "message": f"Copied '{src_path.name}' to '{dst_path}'."}
        except Exception as e:
            return {"status": "error", "message": f"Copy failed: {e}"}

    def move_item(self, source: str, destination: str) -> Dict[str, Any]:
        """Moves a file or directory to a target folder."""
        src_path = Path(source).resolve()
        dst_path = Path(destination).resolve()

        if not src_path.exists():
            return {"status": "error", "message": f"Source '{source}' does not exist."}

        try:
            shutil.move(str(src_path), str(dst_path))
            logger.info(f"Moved '{src_path.name}' to '{dst_path}'.")
            return {"status": "success", "message": f"Moved '{src_path.name}' to '{dst_path}'."}
        except Exception as e:
            return {"status": "error", "message": f"Move failed: {e}"}

    def move_files_by_extension(self, source_dir: str, extension: str, destination_dir: str) -> Dict[str, Any]:
        """
        Moves all files matching an extension from source to destination.
        e.g. 'move all PDFs to Documents'
        """
        src = Path(source_dir).resolve()
        dst = Path(destination_dir).resolve()

        if not src.exists():
            return {"status": "error", "message": f"Source directory '{source_dir}' does not exist."}
        dst.mkdir(parents=True, exist_ok=True)

        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        moved_count = 0

        try:
            for item in src.iterdir():
                if item.is_file() and item.suffix.lower() == ext:
                    shutil.move(str(item), str(dst / item.name))
                    moved_count += 1
            return {
                "status": "success",
                "moved_files": moved_count,
                "message": f"Moved {moved_count} {ext.upper()} files to '{dst.name}'."
            }
        except Exception as e:
            return {"status": "error", "message": f"Batch move failed: {e}"}

    def rename_item(self, file_path: str, new_name: str) -> Dict[str, Any]:
        """Renames a single file or directory."""
        target = Path(file_path).resolve()
        if not target.exists():
            return {"status": "error", "message": f"File '{file_path}' does not exist."}

        # Keep original extension if new_name lacks one
        new_path = target.parent / new_name
        if target.is_file() and not Path(new_name).suffix and target.suffix:
            new_path = target.parent / f"{new_name}{target.suffix}"

        try:
            target.rename(new_path)
            logger.info(f"Renamed '{target.name}' to '{new_path.name}'.")
            return {"status": "success", "message": f"Renamed '{target.name}' to '{new_path.name}'."}
        except Exception as e:
            return {"status": "error", "message": f"Rename failed: {e}"}

    def compress_to_zip(self, target_path: str, output_zip: Optional[str] = None) -> Dict[str, Any]:
        """Creates a ZIP archive of a file or folder."""
        target = Path(target_path).resolve()
        if not target.exists():
            return {"status": "error", "message": f"Target '{target_path}' does not exist."}

        zip_dest = Path(output_zip).resolve() if output_zip else target.parent / f"{target.name}.zip"

        try:
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zipf:
                if target.is_file():
                    zipf.write(target, target.name)
                else:
                    for root, _, files in os.walk(target):
                        for f in files:
                            full_f = Path(root) / f
                            rel_path = full_f.relative_to(target)
                            zipf.write(full_f, rel_path)
            logger.info(f"Compressed '{target.name}' into '{zip_dest.name}'.")
            return {"status": "success", "zip_path": str(zip_dest), "message": f"Created ZIP archive: '{zip_dest.name}'."}
        except Exception as e:
            return {"status": "error", "message": f"Compression failed: {e}"}

    def extract_zip(self, zip_path: str, destination_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts a ZIP archive into a destination folder.
        Protected against Zip Slip path traversal vulnerabilities.
        """
        archive = Path(zip_path).resolve()
        if not archive.exists() or archive.suffix.lower() != ".zip":
            return {"status": "error", "message": f"Invalid zip archive '{zip_path}'."}

        dest = Path(destination_dir).resolve() if destination_dir else archive.parent / archive.stem
        dest.mkdir(parents=True, exist_ok=True)
        dest_resolved = dest.resolve()

        try:
            with zipfile.ZipFile(archive, "r") as zipf:
                # Zip Slip Validation: verify every member path stays within destination directory
                for member in zipf.infolist():
                    target_member_path = (dest / member.filename).resolve()
                    if not str(target_member_path).startswith(str(dest_resolved)):
                        return {
                            "status": "error",
                            "message": f"Security violation: Malicious zip entry detected traversing outside destination: '{member.filename}'"
                        }
                    # Also reject explicit directory traversal sequences
                    if ".." in member.filename.replace("\\", "/").split("/"):
                        return {
                            "status": "error",
                            "message": f"Security violation: Directory traversal member rejected: '{member.filename}'"
                        }

                zipf.extractall(dest)
            logger.info(f"Extracted '{archive.name}' into '{dest.name}'.")
            return {"status": "success", "extracted_path": str(dest), "message": f"Extracted files to folder: '{dest.name}'."}
        except Exception as e:
            return {"status": "error", "message": f"Extraction failed: {e}"}

    def organize_folder(self, target_dir: str) -> Dict[str, Any]:
        """
        Auto-organizes a directory by sorting files into subfolders:
        Documents, Images, Videos, Audio, Archives, Code.
        Protected against organizing project root or critical system directories.
        """
        if not target_dir or target_dir.strip() in [".", "./", ".\\", ""]:
            return {"status": "error", "message": "Refused to organize current working directory / project root. Please provide an explicit folder path."}

        root = Path(target_dir).resolve()
        cwd = Path.cwd().resolve()
        if root == cwd:
            return {"status": "error", "message": f"Refused to organize project repository root '{cwd}'. Please specify a data folder."}

        if not root.exists() or not root.is_dir():
            return {"status": "error", "message": f"Directory '{target_dir}' does not exist."}

        counts = {cat: 0 for cat in self.CATEGORIES}

        try:
            for item in list(root.iterdir()):
                if not item.is_file() or item.name.startswith("."):
                    continue

                ext = item.suffix.lower()
                for cat_name, extensions in self.CATEGORIES.items():
                    if ext in extensions:
                        cat_dir = root / cat_name
                        cat_dir.mkdir(exist_ok=True)
                        try:
                            shutil.move(str(item), str(cat_dir / item.name))
                            counts[cat_name] += 1
                        except (PermissionError, OSError) as pe:
                            logger.warning(f"Skipping locked file '{item.name}': {pe}")
                        break

            total_organized = sum(counts.values())
            summary = ", ".join(f"{cnt} {cat}" for cat, cnt in counts.items() if cnt > 0) or "0 files"
            return {
                "status": "success",
                "total_organized": total_organized,
                "breakdown": counts,
                "message": f"Organized {total_organized} files in '{root.name}' ({summary})."
            }
        except Exception as e:
            return {"status": "error", "message": f"Organization failed: {e}"}


smart_file_manager = SmartFileManager()
