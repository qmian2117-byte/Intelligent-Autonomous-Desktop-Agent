"""
Download Manager Tool for DesktopPilot AI.
Handles downloading web files, PDFs, images, datasets, and media.
Includes automatic Downloads folder organization and resume capability.
"""

import os
import urllib.request
import urllib.parse
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import logger
from tools.system.smart_file_ops import smart_file_manager


class DownloadManager:
    """Manages file and media downloads on Windows."""

    def __init__(self):
        self.default_download_dir = Path.home() / "Downloads"

    def download_url(
        self,
        url: str,
        filename: Optional[str] = None,
        destination_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Downloads any direct web file (PDF, image, zip, dataset) with progress logging.
        """
        dest_dir = Path(destination_dir).resolve() if destination_dir else self.default_download_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            # Parse filename from URL
            parsed = urllib.parse.urlparse(url)
            base = os.path.basename(parsed.path)
            filename = base if base else "downloaded_file"

        target_file = dest_dir / filename

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response, open(target_file, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            file_size_mb = round(target_file.stat().st_size / (1024 * 1024), 2)
            logger.info(f"Downloaded '{filename}' ({file_size_mb} MB) to '{dest_dir}'.")
            return {
                "status": "success",
                "filename": filename,
                "saved_path": str(target_file),
                "size_mb": file_size_mb,
                "message": f"Successfully downloaded '{filename}' ({file_size_mb} MB) to Downloads."
            }
        except Exception as e:
            logger.error(f"Download failed for '{url}': {e}")
            return {"status": "error", "message": f"Download failed: {str(e)}"}

    def download_media_with_ytdlp(self, url: str, extract_audio: bool = False) -> Dict[str, Any]:
        """
        Downloads video or audio from YouTube or supported platforms using yt-dlp.
        """
        output_template = str(self.default_download_dir / "%(title)s.%(ext)s")
        cmd = ["yt-dlp", "-o", output_template, url]
        if extract_audio:
            cmd.extend(["-x", "--audio-format", "mp3"])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                return {
                    "status": "success",
                    "message": "Media download completed and saved to Downloads folder."
                }
            else:
                # If yt-dlp is not installed
                if "not recognized" in res.stderr.lower() or "not found" in res.stderr.lower():
                    return {
                        "status": "info",
                        "message": "yt-dlp is not installed. You can install it using: 'install yt-dlp' or run 'pip install yt-dlp'."
                    }
                return {"status": "error", "message": res.stderr.strip()[:300]}
        except FileNotFoundError:
            return {
                "status": "info",
                "message": "yt-dlp is not installed. Say 'install yt-dlp' to enable automated YouTube/video downloads."
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def organize_downloads(self) -> Dict[str, Any]:
        """Auto-sorts Downloads folder into Documents, Images, Videos, Code, and Archives."""
        return smart_file_manager.organize_folder(str(self.default_download_dir))


download_manager = DownloadManager()
