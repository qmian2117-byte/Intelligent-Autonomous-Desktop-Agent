"""
Verification Node for DesktopPilot AI LangGraph Brain.
Inspects step outcomes to confirm real-world execution success before proceeding.
"""

from typing import Dict, Any
from pathlib import Path
from utils.logger import logger
from tools.desktop.native_input import native_desktop
from agent.states.state import AgentState


async def verifier_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates tool execution output against the step's verification rule.
    Decides whether to advance, retry, or flag an error.
    """
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)

    if idx >= len(plan):
        return {"is_finished": True}

    current_step = plan[idx]
    last_output = state.get("last_tool_output")
    logger.info(f"--- [Verifier Node] Verifying Step {current_step.step_id}: '{current_step.title}' ---")

    is_verified = False
    feedback = ""

    # 1. Verification for Terminal Tool execution
    if isinstance(last_output, dict) and "exit_code" in last_output:
        exit_code = last_output.get("exit_code")
        stdout = str(last_output.get("stdout", ""))
        stderr = str(last_output.get("stderr", ""))

        if exit_code == 0:
            is_verified = True
            feedback = f"Command succeeded with exit code 0. Output: {stdout[:100]}"
        else:
            is_verified = False
            feedback = f"Command failed with exit code {exit_code}. Error: {stderr}"

    # 2. Verification for File Management / Disk Analysis
    elif isinstance(last_output, dict) and "total_scanned_files" in last_output:
        is_verified = True
        feedback = f"Disk analysis completed successfully. Scanned {last_output['total_scanned_files']} files."

    # 3. Verification for Application Launch (Confirm window is active on desktop)
    elif current_step.tool_name in ["open_app", "open_anything", "launch_vscode"]:
        target_name = (
            (current_step.tool_parameters or {}).get("app_name") or
            (current_step.tool_parameters or {}).get("target") or
            ""
        )
        active_win = native_desktop.get_active_window_title().lower()
        hwnd = native_desktop.find_window_by_title(target_name) if target_name else None
        if hwnd or (target_name and target_name.lower() in active_win):
            is_verified = True
            feedback = f"Window '{target_name}' is verified present/active on desktop."
        elif last_output and not str(last_output).startswith("Error"):
            is_verified = True
            feedback = f"Launch command verified successfully: {last_output}"
        else:
            is_verified = False
            feedback = f"Target application '{target_name}' window was not detected."

    # 4. Verification for File Creation / Modification
    elif current_step.tool_name in ["file_copy", "file_rename", "file_compress_zip", "file_extract_zip"]:
        dest = (
            (current_step.tool_parameters or {}).get("destination") or
            (current_step.tool_parameters or {}).get("new_name") or
            (current_step.tool_parameters or {}).get("destination_dir") or
            ""
        )
        if dest and Path(dest).exists():
            is_verified = True
            feedback = f"File verification passed: '{dest}' exists on disk."
        elif last_output and isinstance(last_output, dict) and last_output.get("status") == "success":
            is_verified = True
            feedback = last_output.get("message", "File operation completed.")
        else:
            is_verified = False
            feedback = f"File operation failed or destination '{dest}' not found."

    # 5. Verification for Generic Output
    elif last_output is not None and not str(last_output).startswith("Error"):
        is_verified = True
        feedback = f"Step executed without errors: {str(last_output)[:100]}"
    else:
        is_verified = False
        feedback = f"Execution returned error: {str(last_output)}"

    logger.info(f"Verification result: {'PASSED' if is_verified else 'FAILED'} | {feedback}")

    if is_verified:
        current_step.status = "verified"
        current_step.is_completed = True
        next_index = idx + 1
        is_finished = next_index >= len(plan)

        return {
            "step_verified": True,
            "verification_feedback": feedback,
            "current_step_index": next_index,
            "retry_count": 0,
            "is_finished": is_finished,
            "final_summary": f"Completed all {len(plan)} steps successfully." if is_finished else None
        }
    else:
        current_step.status = "failed"
        current_step.error = feedback
        retry_count = state.get("retry_count", 0) + 1

        return {
            "step_verified": False,
            "verification_feedback": feedback,
            "retry_count": retry_count,
            "is_finished": False
        }
