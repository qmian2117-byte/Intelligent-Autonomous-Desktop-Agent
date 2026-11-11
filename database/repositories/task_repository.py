"""
Task & Action Audit Repository for DesktopPilot AI.
Provides clean DAO abstractions for saving and querying task runs, tool actions, and approvals.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from database.session import async_session_factory
from database.models.audit import TaskRun, ActionAuditLog, ApprovalRecord
from utils.logger import logger


class TaskRepository:
    """Repository handling audit trails and execution histories."""

    @staticmethod
    async def create_task(task_id: str, user_goal: str) -> Optional[TaskRun]:
        """Records a new task run in the database."""
        if not async_session_factory:
            return None
        try:
            async with async_session_factory() as session:
                task = TaskRun(id=task_id, user_goal=user_goal, status="running")
                session.add(task)
                await session.commit()
                return task
        except Exception as e:
            logger.warning(f"Could not persist task creation: {e}")
            return None

    @staticmethod
    async def log_tool_action(
        task_id: str,
        step_id: int,
        tool_name: str,
        parameters: Dict[str, Any],
        result_preview: str,
        exit_code: Optional[int] = None,
        is_blocked: bool = False,
        execution_time: float = 0.0
    ):
        """Logs an individual tool execution to the audit log."""
        if not async_session_factory:
            return
        try:
            async with async_session_factory() as session:
                action = ActionAuditLog(
                    task_id=task_id,
                    step_id=step_id,
                    tool_name=tool_name,
                    parameters_json=json.dumps(parameters),
                    result_preview=result_preview[:500] if result_preview else "",
                    exit_code=exit_code,
                    is_blocked=is_blocked,
                    execution_time_seconds=execution_time
                )
                session.add(action)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist action audit log: {e}")

    @staticmethod
    async def record_approval(task_id: str, token: str, prompt: str):
        """Records a Human-in-the-Loop approval request."""
        if not async_session_factory:
            return
        try:
            async with async_session_factory() as session:
                rec = ApprovalRecord(
                    task_id=task_id,
                    token=token,
                    prompt=prompt,
                    status="pending"
                )
                session.add(rec)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist approval record: {e}")


task_repository = TaskRepository()
