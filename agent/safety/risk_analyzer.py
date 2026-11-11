"""
AI Safety Layer & Risk Analyzer for DesktopPilot AI.
Classifies all autonomous actions into LOW, MEDIUM, or HIGH risk tiers.
Enforces zero-tolerance policies on system destruction and malware behavior.
"""

import re
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from utils.logger import logger


class RiskLevel(str, Enum):
    LOW = "low"            # Auto-execute (read-only, navigation, whitelisted apps)
    MEDIUM = "medium"      # Require user approval (file modifications, installs, closures)
    HIGH = "high_blocked"  # Block immediately (system destruction, formatting, malware)


class RiskAssessment(BaseModel):
    level: RiskLevel
    reason: str
    requires_approval: bool
    confirmation_prompt: Optional[str] = None
    matched_rule: Optional[str] = None


class DesktopSafetyAnalyzer:
    """
    Evaluates actions before they touch the operating system.
    Guarantees no accidental formatting, system file deletion, or malware patterns.
    """

    # 1. HIGH RISK (Strict Blocklist) - Zero Tolerance
    HIGH_RISK_COMMANDS = [
        (r"\bformat\s+[a-zA-Z]:", "Disk formatting attempt"),
        (r"\brmdir\s+/[sS]\s+/[qQ]\s+[cC]:\\", "Root system drive wipe"),
        (r"\bdel\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\", "System drive bulk deletion"),
        (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bomb denial of service"),
        (r"\bdiskpart\b", "Low-level disk partitioning"),
        (r"\bvssadmin\s+delete\s+shadows", "Ransomware-like shadow copy deletion"),
        (r"\bbcdedit\b", "Boot configuration modification"),
        (r"\breg\s+delete\s+HKLM", "Critical Windows registry hive deletion"),
        (r"\bshutdown\s+/[sSrR]", "System shutdown / reboot command"),
        (r"\bInvoke-WebRequest.*\.exe\b", "Unverified remote executable download"),
        (r"\bcurl.*\|.*powershell\b", "Remote script piped directly to shell"),
    ]

    # Critical Windows operating system processes that can NEVER be killed
    PROTECTED_SYSTEM_PROCESSES = {
        "explorer.exe", "csrss.exe", "smss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe", "dwm.exe",
        "ntoskrnl.exe", "winlogon.exe", "system"
    }

    # Protected system directories that can NEVER be deleted or modified
    PROTECTED_SYSTEM_DIRECTORIES = [
        r"C:\Windows",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
        r"C:\ProgramData\Microsoft",
        r"C:\Boot",
        r"C:\Recovery"
    ]

    # 2. MEDIUM RISK (Requires Human Approval)
    MEDIUM_RISK_COMMANDS = [
        (r"\bwinget\s+install\b", "Package installation via Windows Package Manager"),
        (r"\bchoco\s+install\b", "Package installation via Chocolatey"),
        (r"\bnpm\s+install\s+-g\b", "Global package installation"),
        (r"\bpip\s+install\b", "Python package installation"),
        (r"\bgit\s+clean\s+-fd\b", "Untracked file deletion in git"),
        (r"\bRemove-Item\b", "File deletion in PowerShell"),
        (r"\bdel\b", "File deletion in CMD"),
        (r"\bSet-ExecutionPolicy\b", "PowerShell execution policy modification"),
        (r"\bnet\s+user\b", "User account modification"),
    ]

    @classmethod
    def evaluate_command(cls, command: str) -> RiskAssessment:
        """Analyzes a terminal command string against security rules."""
        cmd = command.strip()

        # Check HIGH risk patterns (Block immediately)
        for pattern, description in cls.HIGH_RISK_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                logger.warning(f"HIGH RISK BLOCKED: '{cmd}' matches {description}")
                return RiskAssessment(
                    level=RiskLevel.HIGH,
                    reason=f"Security Policy Violation: {description}",
                    requires_approval=False,
                    matched_rule=pattern
                )

        # Check MEDIUM risk patterns (Ask confirmation)
        for pattern, description in cls.MEDIUM_RISK_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                logger.info(f"MEDIUM RISK INTERCEPT: '{cmd}' matches {description}")
                return RiskAssessment(
                    level=RiskLevel.MEDIUM,
                    reason=f"Potentially impactful action: {description}",
                    requires_approval=True,
                    confirmation_prompt=f"The agent wants to run: `{cmd}` ({description}). Do you approve?",
                    matched_rule=pattern
                )

        # Default: LOW risk (Auto-execute safe command)
        return RiskAssessment(
            level=RiskLevel.LOW,
            reason="Standard read-only or low-impact operation.",
            requires_approval=False
        )

    @classmethod
    def evaluate_file_action(cls, operation: str, target_path: str) -> RiskAssessment:
        """Inspects file modifications or deletions."""
        resolved = Path(target_path).resolve()
        resolved_str = str(resolved).lower()

        # Check if targeting protected system directories
        for protected in cls.PROTECTED_SYSTEM_DIRECTORIES:
            if resolved_str.startswith(protected.lower()):
                return RiskAssessment(
                    level=RiskLevel.HIGH,
                    reason=f"Access Denied: Cannot modify protected system path '{target_path}'.",
                    requires_approval=False
                )

        if operation.lower() in ["delete", "remove", "wipe"]:
            return RiskAssessment(
                level=RiskLevel.MEDIUM,
                reason=f"Deletion requested for file/folder '{target_path}'.",
                requires_approval=True,
                confirmation_prompt=f"DesktopPilot AI requests approval to delete: {target_path}"
            )

        return RiskAssessment(
            level=RiskLevel.LOW,
            reason="Safe file read/scan operation.",
            requires_approval=False
        )

    @classmethod
    def evaluate_process_termination(cls, process_name: str) -> RiskAssessment:
        """Inspects request to close or kill an application."""
        normalized = process_name.lower().strip()
        if not normalized.endswith(".exe"):
            normalized += ".exe"

        # Check protected core OS processes
        if normalized in cls.PROTECTED_SYSTEM_PROCESSES:
            return RiskAssessment(
                level=RiskLevel.HIGH,
                reason=f"Blocked: Terminating core system process '{process_name}' would crash Windows.",
                requires_approval=False
            )

        # Safe user applications (VS Code, Chrome, etc.) require confirmation to avoid unsaved work
        return RiskAssessment(
            level=RiskLevel.MEDIUM,
            reason=f"Closing active user application '{process_name}'.",
            requires_approval=True,
            confirmation_prompt=f"Do you want to close '{process_name}'? Ensure all work is saved."
        )


# Global safety analyzer instance
safety_analyzer = DesktopSafetyAnalyzer()

