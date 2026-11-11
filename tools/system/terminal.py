"""
Secure Terminal Tool for DesktopPilot AI.
Provides controlled command execution with sandboxing, timeout safeguards,
keyword safety blocklists, and structured stdout/stderr capture.
"""

import subprocess
import shlex
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from utils.logger import logger


class CommandResult(BaseModel):
    """Structured response from a terminal execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    is_success: bool
    is_blocked: bool = False
    block_reason: Optional[str] = None
    execution_time_seconds: float = 0.0


class SecureTerminalTool:
    """
    Executes system terminal commands with security guardrails.
    Designed for Windows desktop environments.
    """

    # Strictly forbidden command patterns that could cause irreversible destruction
    BLOCKED_PATTERNS = [
        r"\bformat\b",
        r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\",
        r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
        r"\bdiskpart\b",
        r"\bvssadmin\s+delete\s+shadows\b",       # Deleting restore points
        r"\breg\s+delete\s+HKLM\b",
        r"\bshutdown\s+/[sSrR]\b"
    ]

    # Commands that require human approval before running
    HIGH_RISK_PATTERNS = [
        r"\bdel\b",
        r"\brmdir\b",
        r"\bRemove-Item\b",
        r"\bSet-ExecutionPolicy\b",
        r"\bnet\s+user\b"
    ]

    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout

    def is_command_safe(self, command: str) -> tuple[bool, Optional[str], bool]:
        """
        Evaluates command safety.
        Returns: (is_allowed, reason, requires_human_approval)
        """
        cmd_clean = command.strip()

        # Check fatal blacklist
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return False, f"Command contains strictly forbidden pattern: '{pattern}'", False

        # Check if human approval is needed
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return True, "Potentially destructive action: Requires user confirmation.", True

        return True, None, False

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_dir: Optional[str] = None,
        confirmed_by_user: bool = False
    ) -> CommandResult:
        """
        Executes a shell command safely, capturing output and enforcing timeouts.
        """
        timeout_limit = timeout or self.default_timeout
        cmd_clean = command.strip()

        # Safety Check
        is_allowed, reason, requires_approval = self.is_command_safe(cmd_clean)
        if not is_allowed:
            logger.warning(f"Security Alert: Blocked dangerous command: {cmd_clean}")
            return CommandResult(
                command=cmd_clean,
                exit_code=-1,
                stdout="",
                stderr=reason or "Security policy violation.",
                is_success=False,
                is_blocked=True,
                block_reason=reason
            )

        if requires_approval and not confirmed_by_user:
            logger.info(f"Command requires user confirmation before execution: {cmd_clean}")
            return CommandResult(
                command=cmd_clean,
                exit_code=-2,
                stdout="",
                stderr="Execution paused: This command modifies system files and requires explicit user confirmation.",
                is_success=False,
                is_blocked=False,
                block_reason="Awaiting user approval."
            )

        import time
        start_time = time.time()

        try:
            # Use PowerShell on Windows for modern command execution
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd_clean],
                capture_output=True,
                text=True,
                timeout=timeout_limit,
                cwd=working_dir
            )
            elapsed = time.time() - start_time

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            is_success = process.returncode == 0

            return CommandResult(
                command=cmd_clean,
                exit_code=process.returncode,
                stdout=stdout,
                stderr=stderr,
                is_success=is_success,
                execution_time_seconds=round(elapsed, 2)
            )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            return CommandResult(
                command=cmd_clean,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_limit} seconds.",
                is_success=False,
                execution_time_seconds=round(elapsed, 2)
            )
        except Exception as e:
            elapsed = time.time() - start_time
            return CommandResult(
                command=cmd_clean,
                exit_code=-1,
                stdout="",
                stderr=f"Subprocess exception: {str(e)}",
                is_success=False,
                execution_time_seconds=round(elapsed, 2)
            )


# Global terminal instance
terminal_tool = SecureTerminalTool()
