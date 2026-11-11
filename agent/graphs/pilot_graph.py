"""
Main LangGraph StateGraph Assembly for DesktopPilot AI Brain.
Connects Planner, Executor, Verifier, and Human-in-the-Loop conditional routing.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.states.state import AgentState
from agent.nodes.planner import planner_node
from agent.nodes.executor import executor_node
from agent.nodes.verifier import verifier_node


def route_after_executor(state: AgentState) -> Literal["verifier", "__end__"]:
    """Routes execution after the Executor runs."""
    if state.get("requires_approval", False):
        # In production with LangGraph, this triggers an interrupt for HITL
        return "__end__"
    return "verifier"


def route_after_verifier(state: AgentState) -> Literal["executor", "planner", "__end__"]:
    """
    Decides next node based on verification outcome:
    - If all steps finished -> END
    - If verified -> proceed to next step in Executor
    - If failed & retries left -> retry step in Executor
    - If failed & retries exhausted -> Re-plan in Planner
    """
    if state.get("is_finished", False):
        return "__end__"

    if state.get("step_verified", False):
        return "executor"

    max_retries = state.get("max_retries", 2)
    current_retries = state.get("retry_count", 0)

    if current_retries <= max_retries:
        return "executor"
    else:
        return "planner"  # Trigger re-planning


def create_pilot_agent_graph():
    """
    Builds and compiles the complete LangGraph StateGraph.
    """
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("verifier", verifier_node)

    # Define Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")

    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "verifier": "verifier",
            "__end__": END
        }
    )

    workflow.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "executor": "executor",
            "planner": "planner",
            "__end__": END
        }
    )

    # Use in-memory checkpointer for state management and time-travel replay
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app


# Pre-compiled agent graph instance
pilot_agent_graph = create_pilot_agent_graph()

