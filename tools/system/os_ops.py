"""
Operating system automation tools for DesktopPilot AI.
Handles application launching, window detection, and safe OS operations.
"""

import subprocess
import shutil
from typing import Dict, Any, Optional
from utils.logger import logger


class SystemTools:
    """Safe system execution tools."""

    @staticmethod
    def launch_app(app_name: str) -> Dict[str, Any]:
        """
        Launches an application by name or system command (e.g. 'notepad', 'calc', 'chrome').
        """
        try:
            # Check if app exists on PATH or use shell start
            process = subprocess.Popen(
                ["cmd", "/c", "start", "", app_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False
            )
            logger.info(f"Launched application: {app_name}")
            return {"status": "success", "message": f"Application '{app_name}' launched."}
        except Exception as e:
            logger.error(f"Failed to launch '{app_name}': {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def run_safe_command(command: str) -> Dict[str, Any]:
        """
        Executes a non-destructive shell command and returns output.
        Blocks destructive keywords.
        """
        blocked_keywords = ["del /f", "format", "rmdir /s", "drop database", "shutdown"]
        for blocked in blocked_keywords:
            if blocked in command.lower():
                return {"status": "blocked", "message": f"Execution blocked: Command contains forbidden keyword '{blocked}'."}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15
            )
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Command timed out after 15 seconds."}
        except Exception as e:
            return {"status": "error", "message": str(e)}


system_tools = SystemTools()
