"""
Planner Node for DesktopPilot AI LangGraph Brain.
Deconstructs high-level user goals into structured, ordered action steps.
"""

import json
import re
from typing import Dict, Any, List
from utils.logger import logger

from agent.states.state import AgentState, Step
from models.ollama.llm_service import llm_service
from tools.registry import tool_registry


PLANNER_SYSTEM_PROMPT = """You are the Lead Planner Agent for DesktopPilot AI.
Your job is to deconstruct the user's high-level desktop goal into a list of atomic executable steps.

AVAILABLE TOOLS:
{tools}

RULES:
1. Break the task down logically. Example for "Install n8n":
   - Step 1: Check if Node.js is installed (`run_terminal_command` with 'node --version')
   - Step 2: Install n8n globally (`run_terminal_command` with 'npm install -g n8n')
   - Step 3: Verify n8n installation (`run_terminal_command` with 'n8n --version')
2. Output ONLY a valid JSON array of step objects. No markdown outside JSON.

JSON SCHEMA:
[
  {{
    "step_id": 1,
    "title": "Short title",
    "tool_name": "tool_name_from_list",
    "tool_parameters": {{"param": "value"}},
    "verification_rule": "What stdout or condition proves this step succeeded"
  }}
]
"""


async def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes user_goal and produces an ordered step-by-step execution plan.
    If a previous step failed verification, replans the remaining steps.
    """
    logger.info(f"--- [Planner Node] Planning for goal: '{state['user_goal']}' ---")

    # If plan already exists and we are replanning after failure
    if state.get("plan") and not state.get("step_verified", True):
        prompt = f"""The previous step failed verification.
Goal: {state['user_goal']}
Failed Step: {state['plan'][state['current_step_index']].title}
Error/Feedback: {state.get('verification_feedback')}

Please provide a revised remaining plan to overcome this failure.
Output ONLY the JSON list of remaining steps.
"""
    else:
        prompt = f"Goal: {state['user_goal']}\nGenerate the complete step-by-step JSON plan."

    tools_desc = tool_registry.get_tool_descriptions()
    system_prompt = PLANNER_SYSTEM_PROMPT.format(tools=tools_desc)

    raw_response = await llm_service.chat(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system_prompt,
        temperature=0.1
    )

    # Parse JSON from response
    steps: List[Step] = []
    try:
        # Extract json array using regex
        match = re.search(r"\[.*\]", raw_response, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            for item in parsed:
                steps.append(
                    Step(
                        step_id=item.get("step_id", len(steps) + 1),
                        title=item.get("title", "Execute action"),
                        tool_name=item.get("tool_name"),
                        tool_parameters=item.get("tool_parameters", {}),
                        verification_rule=item.get("verification_rule"),
                        status="pending"
                    )
                )
    except Exception as e:
        logger.error(f"Planner JSON parsing error: {e}. Fallback to direct terminal execution.")
        # Fallback single-step plan
        steps = [
            Step(
                step_id=1,
                title=f"Execute: {state['user_goal']}",
                tool_name="run_terminal_command",
                tool_parameters={"command": state['user_goal']},
                verification_rule="Exit code 0",
                status="pending"
            )
        ]

    logger.info(f"Plan generated with {len(steps)} steps.")
    return {
        "plan": steps,
        "current_step_index": 0,
        "retry_count": 0,
        "is_finished": False
    }
