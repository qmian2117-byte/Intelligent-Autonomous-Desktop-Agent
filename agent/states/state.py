"""
State definitions for DesktopPilot AI LangGraph Agent Brain.
"""

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

try:
    from langgraph.graph.message import add_messages
except ImportError:
    # Fallback message reducer when langgraph is not installed in the active environment
    def add_messages(left: list, right: list) -> list:
        return list(left) + list(right)


class Step(BaseModel):
    step_id: int
    title: str
    tool_name: Optional[str] = None
    tool_parameters: Dict[str, Any] = Field(default_factory=dict)
    is_completed: bool = False
    status: str = "pending"  # pending, executing, verified, failed
    verification_rule: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentState(TypedDict):
    """
    Main State Machine schema passed across Planner, Executor, and Verifier.
    """
    # Conversation history
    messages: Annotated[list, add_messages]

    # Goal and Plan
    user_goal: str
    plan: List[Step]
    current_step_index: int

    # Execution data
    last_tool_executed: Optional[str]
    last_tool_output: Optional[Any]
    retry_count: int
    max_retries: int

    # Verification status
    step_verified: bool
    verification_feedback: Optional[str]

    # Human-in-the-loop Governance
    requires_approval: bool
    approval_token: Optional[str]
    approval_prompt: Optional[str]
    is_approved: Optional[bool]

    # Final lifecycle
    is_finished: bool
    final_summary: Optional[str]
