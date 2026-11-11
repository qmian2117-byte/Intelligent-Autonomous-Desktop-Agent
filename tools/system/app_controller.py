"""
Application Control Tool for DesktopPilot AI.
Provides controlled application launching, graceful closing, VS Code integration,
browser navigation, and project command execution within an approved whitelist.
"""

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from agent.safety.risk_analyzer import safety_analyzer, RiskLevel
from utils.logger import logger


class AppControlResult(BaseModel):
    action: str
    target: str
    is_success: bool
    message: str
    pid: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class ApplicationController:
    """
    Manages desktop applications with whitelist enforcement and safety checks.
    """

    # Approved application whitelist with execution commands/aliases
    APPLICATION_WHITELIST = {
        # IDEs & Editors
        "code": {"name": "Visual Studio Code", "cmd": "code", "process": "Code.exe"},
        "vscode": {"name": "Visual Studio Code", "cmd": "code", "process": "Code.exe"},
        "notepad": {"name": "Notepad", "cmd": "notepad.exe", "process": "notepad.exe"},
        "notepad++": {"name": "Notepad++", "cmd": "notepad++.exe", "process": "notepad++.exe"},

        # Web Browsers
        "chrome": {"name": "Google Chrome", "cmd": "chrome", "process": "chrome.exe"},
        "google-chrome": {"name": "Google Chrome", "cmd": "chrome", "process": "chrome.exe"},
        "edge": {"name": "Microsoft Edge", "cmd": "msedge", "process": "msedge.exe"},
        "msedge": {"name": "Microsoft Edge", "cmd": "msedge", "process": "msedge.exe"},
        "browser": {"name": "Default Browser", "cmd": "default_browser", "process": ""},

        # System Utilities & Terminal
        "calculator": {"name": "Windows Calculator", "cmd": "calc.exe", "process": "CalculatorApp.exe"},
        "calc": {"name": "Windows Calculator", "cmd": "calc.exe", "process": "CalculatorApp.exe"},
        "terminal": {"name": "Windows Terminal", "cmd": "wt.exe", "process": "WindowsTerminal.exe"},
        "cmd": {"name": "Command Prompt", "cmd": "cmd.exe", "process": "cmd.exe"},
        "powershell": {"name": "PowerShell", "cmd": "powershell.exe", "process": "powershell.exe"},
        "explorer": {"name": "File Explorer", "cmd": "explorer.exe", "process": "explorer.exe"},

        # Developer Tools
        "git": {"name": "Git", "cmd": "git", "process": "git.exe"},
        "docker": {"name": "Docker Desktop", "cmd": "Docker Desktop.exe", "process": "Docker Desktop.exe"}
    }

    @classmethod
    def launch_app(cls, app_name: str, arguments: Optional[str] = None) -> AppControlResult:
        """
        Launches an application verified against the whitelist.
        """
        normalized = app_name.lower().strip()
        app_spec = cls.APPLICATION_WHITELIST.get(normalized)

        if not app_spec:
            whitelist_keys = ", ".join(cls.APPLICATION_WHITELIST.keys())
            return AppControlResult(
                action="launch",
                target=app_name,
                is_success=False,
                message=f"Application '{app_name}' is not in the approved whitelist. Whitelisted: [{whitelist_keys}]"
            )

        cmd = app_spec["cmd"]
        full_command = f"{cmd} {arguments}".strip() if arguments else cmd

        try:
            pid = None
            if not arguments and cmd in ["notepad.exe", "calc.exe", "explorer.exe"]:
                try:
                    os.startfile(cmd)
                except Exception:
                    process = subprocess.Popen([cmd], shell=False)
                    pid = process.pid
            else:
                args = [cmd] + ([arguments] if arguments else [])
                process = subprocess.Popen(args, shell=True)
                pid = process.pid

            logger.info(f"Launched application '{app_spec['name']}' ({cmd})")
            return AppControlResult(
                action="launch",
                target=app_spec["name"],
                is_success=True,
                message=f"Successfully launched {app_spec['name']}.",
                pid=pid
            )
        except Exception as e:
            logger.error(f"Failed to launch '{app_name}': {e}")
            return AppControlResult(
                action="launch",
                target=app_name,
                is_success=False,
                message=f"System error launching application: {str(e)}"
            )

    @classmethod
    def close_app(cls, app_name: str, force: bool = False, confirmed: bool = False) -> AppControlResult:
        """
        Closes an active application after passing through the safety analyzer.
        """
        normalized = app_name.lower().strip()
        app_spec = cls.APPLICATION_WHITELIST.get(normalized)
        process_name = app_spec["process"] if app_spec and app_spec["process"] else app_name

        # Safety evaluation
        assessment = safety_analyzer.evaluate_process_termination(process_name)
        if assessment.level == RiskLevel.HIGH:
            return AppControlResult(
                action="close",
                target=process_name,
                is_success=False,
                message=f"Action Blocked by Safety Layer: {assessment.reason}"
            )

        if assessment.requires_approval and not confirmed:
            return AppControlResult(
                action="close",
                target=process_name,
                is_success=False,
                message=f"Confirmation Required: {assessment.confirmation_prompt}"
            )

        try:
            flag = "/f" if force else ""
            cmd = ["taskkill"]
            if force:
                cmd.append("/f")
            cmd.extend(["/im", process_name if process_name.endswith(".exe") else f"{process_name}.exe"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logger.info(f"Closed application: {process_name}")
                return AppControlResult(
                    action="close",
                    target=process_name,
                    is_success=True,
                    message=f"Successfully closed {process_name}."
                )
            else:
                return AppControlResult(
                    action="close",
                    target=process_name,
                    is_success=False,
                    message=f"Failed to close {process_name}: {result.stderr.strip() or 'Process may not be running.'}"
                )
        except Exception as e:
            return AppControlResult(
                action="close",
                target=process_name,
                is_success=False,
                message=f"Error closing application: {str(e)}"
            )

    @classmethod
    def launch_vscode(cls, project_path: Optional[str] = None) -> AppControlResult:
        """
        Launches Visual Studio Code directly, optionally opening a specific folder.
        """
        target_path = project_path or "."
        resolved = Path(target_path).resolve()

        if not resolved.exists():
            return AppControlResult(
                action="launch_vscode",
                target=str(resolved),
                is_success=False,
                message=f"Project path does not exist: {resolved}"
            )

        try:
            subprocess.Popen(["code", str(resolved)], shell=True)
            logger.info(f"VS Code launched opening: {resolved}")
            return AppControlResult(
                action="launch_vscode",
                target=str(resolved),
                is_success=True,
                message=f"Visual Studio Code launched with directory: {resolved}"
            )
        except Exception as e:
            return AppControlResult(
                action="launch_vscode",
                target=str(resolved),
                is_success=False,
                message=f"Failed to launch VS Code: {str(e)}. Ensure 'code' is in your system PATH."
            )

    @classmethod
    def open_browser(cls, url: Optional[str] = None) -> AppControlResult:
        """
        Opens the system web browser in a brand new foreground window.
        Uses native Windows shell start with fallback across Chrome, Edge, and default browser.
        """
        target_url = url or "https://www.google.com"

        # Validate URL scheme to prevent file injection
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            target_url = f"https://{target_url}"

        try:
            try:
                os.startfile(target_url)
            except Exception:
                webbrowser.open_new(target_url)

            logger.info(f"Opened browser via ShellExecute to URL: {target_url}")
            return AppControlResult(
                action="open_browser",
                target=target_url,
                is_success=True,
                message=f"Browser opened to: {target_url}"
            )
        except Exception as e:
            return AppControlResult(
                action="open_browser",
                target=target_url,
                is_success=False,
                message=f"Failed to open browser: {str(e)}"
            )

    @classmethod
    def run_project_command(
        cls,
        command: str,
        project_dir: Optional[str] = None,
        confirmed: bool = False
    ) -> AppControlResult:
        """
        Executes a project development command (e.g. 'npm run dev', 'pytest', 'pip install -r requirements.txt').
        Enforces safety checks before execution.
        """
        work_dir = Path(project_dir or ".").resolve()
        if not work_dir.exists():
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=False,
                message=f"Project directory not found: {work_dir}"
            )

        # Safety evaluation
        assessment = safety_analyzer.evaluate_command(command)
        if assessment.level == RiskLevel.HIGH:
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=False,
                message=f"Blocked by Safety Layer: {assessment.reason}"
            )

        if assessment.requires_approval and not confirmed:
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=False,
                message=f"Confirmation Required: {assessment.confirmation_prompt}"
            )

        try:
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=process.returncode == 0,
                message="Command finished successfully." if process.returncode == 0 else "Command exited with error.",
                stdout=process.stdout.strip(),
                stderr=process.stderr.strip()
            )
        except subprocess.TimeoutExpired:
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=False,
                message="Execution timed out after 60 seconds."
            )
        except Exception as e:
            return AppControlResult(
                action="run_project_command",
                target=command,
                is_success=False,
                message=f"Execution error: {str(e)}"
            )


# Global controller instance
app_controller = ApplicationController()

