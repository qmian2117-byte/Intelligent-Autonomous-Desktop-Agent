"""
Executor Node for DesktopPilot AI LangGraph Brain.
Executes the tool for the active step in the plan with safety checks.
"""

from typing import Dict, Any
from utils.logger import logger

from agent.states.state import AgentState
from tools.registry import tool_registry


async def executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieves the current step from the plan and dispatches tool execution.
    """
    plan = state.get("plan", [])
    idx = state.get("current_step_index", 0)

    if idx >= len(plan):
        return {
            "is_finished": True,
            "final_summary": "All planned steps have been executed."
        }

    current_step = plan[idx]
    logger.info(f"--- [Executor Node] Executing Step {current_step.step_id}: '{current_step.title}' ---")
    logger.info(f"Tool: {current_step.tool_name} | Params: {current_step.tool_parameters}")

    tool_name = current_step.tool_name
    params = current_step.tool_parameters or {}

    # Safety check: if disk cleanup or high-risk command without approval
    if tool_name == "confirm_disk_cleanup" and not state.get("is_approved"):
        logger.warning("Safety Intercept: confirm_disk_cleanup requires explicit human approval.")
        return {
            "requires_approval": True,
            "approval_prompt": "Disk cleanup requires confirmation. Do you approve deleting the identified temporary files?",
            "approval_token": params.get("confirmation_token")
        }

    # Execute tool
    result = tool_registry.execute(tool_name, **params)

    # Check if tool itself reported blocked or requires confirmation
    if isinstance(result, dict) and result.get("exit_code") == -2:
        return {
            "requires_approval": True,
            "approval_prompt": result.get("stderr"),
            "last_tool_executed": tool_name,
            "last_tool_output": result
        }

    current_step.status = "executing"
    current_step.result = result

    return {
        "last_tool_executed": tool_name,
        "last_tool_output": result,
        "requires_approval": False
    }
