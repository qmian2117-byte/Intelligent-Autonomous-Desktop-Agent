"""
API endpoints for DesktopPilot AI task execution and control.
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

try:
    from agent.graphs.pilot_graph import pilot_agent_graph
except ImportError:
    pilot_agent_graph = None

from models.ollama.llm_service import llm_service
from tools.registry import tool_registry
from api.websocket.stream import telemetry_manager
from utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["Agent Operations"])


class TaskRunRequest(BaseModel):
    goal: str = Field(..., description="High-level instruction for DesktopPilot AI")


class TaskApprovalRequest(BaseModel):
    token: str = Field(..., description="Confirmation token for high-risk action")
    approved: bool = Field(..., description="True to execute, False to abort")


# Active execution cache for demonstration / state query
ACTIVE_TASKS: Dict[str, Dict[str, Any]] = {}


async def _run_agent_pipeline(task_id: str, goal: str):
    """Executes the compiled LangGraph workflow in the background and streams telemetry."""
    await telemetry_manager.broadcast("task_started", {"task_id": task_id, "goal": goal})

    initial_state = {
        "messages": [],
        "user_goal": goal,
        "plan": [],
        "current_step_index": 0,
        "last_tool_executed": None,
        "last_tool_output": None,
        "retry_count": 0,
        "max_retries": 2,
        "step_verified": False,
        "verification_feedback": None,
        "requires_approval": False,
        "approval_token": None,
        "approval_prompt": None,
        "is_approved": None,
        "is_finished": False,
        "final_summary": None
    }

    config = {"configurable": {"thread_id": task_id}}

    try:
        # Stream intermediate graph events token-by-token and node-by-node
        async for event in pilot_agent_graph.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                logger.info(f"LangGraph node transition: {node_name}")
                await telemetry_manager.broadcast(
                    "node_transition",
                    {
                        "task_id": task_id,
                        "node": node_name,
                        "current_step": state_update.get("current_step_index"),
                        "requires_approval": state_update.get("requires_approval", False)
                    }
                )

                # Check if paused for human approval
                if state_update.get("requires_approval"):
                    ACTIVE_TASKS[task_id]["status"] = "paused_for_approval"
                    ACTIVE_TASKS[task_id]["approval_token"] = state_update.get("approval_token")
                    await telemetry_manager.broadcast(
                        "approval_required",
                        {
                            "task_id": task_id,
                            "prompt": state_update.get("approval_prompt"),
                            "token": state_update.get("approval_token")
                        }
                    )
                    return

        ACTIVE_TASKS[task_id]["status"] = "completed"
        await telemetry_manager.broadcast("task_completed", {"task_id": task_id})

    except Exception as e:
        logger.error(f"Error running task {task_id}: {e}")
        ACTIVE_TASKS[task_id]["status"] = "failed"
        ACTIVE_TASKS[task_id]["error"] = str(e)
        await telemetry_manager.broadcast("task_failed", {"task_id": task_id, "error": str(e)})


@router.post("/agent/run")
async def run_agent_task(request: TaskRunRequest, background_tasks: BackgroundTasks):
    """
    Triggers an autonomous desktop automation task.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    ACTIVE_TASKS[task_id] = {
        "task_id": task_id,
        "goal": request.goal,
        "status": "queued"
    }

    background_tasks.add_task(_run_agent_pipeline, task_id, request.goal)
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": f"Task '{request.goal}' initiated in background."
    }


@router.get("/agent/tasks")
async def list_tasks():
    """Lists recent tasks and statuses."""
    return list(ACTIVE_TASKS.values())


@router.get("/agent/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Fetches details of a specific task run."""
    if task_id not in ACTIVE_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return ACTIVE_TASKS[task_id]


@router.post("/agent/approve")
async def submit_human_approval(request: TaskApprovalRequest):
    """
    Submits a human approval decision for high-risk actions.
    """
    return {
        "status": "received",
        "token": request.token,
        "decision": "approved" if request.approved else "rejected"
    }


@router.get("/tools")
async def list_available_tools():
    """Returns documentation and schemas for all active tools in the registry."""
    return tool_registry._schemas


@router.get("/health")
async def system_health_check():
    """Verifies backend, Ollama server, and Llama 3.1 8B presence."""
    ollama_health = await llm_service.check_health()
    return {
        "backend": "online",
        "version": "0.1.0",
        "ollama": ollama_health
    }

