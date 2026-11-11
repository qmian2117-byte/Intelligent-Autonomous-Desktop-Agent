"""
Test verifying Autonomous Screen Pilot with Decision Making and Physical Typing.
"""

import asyncio
from agent.autonomous_pilot import autonomous_pilot


async def test_notepad_autonomous_flow():
    print("=== Testing Autonomous Screen Pilot: Notepad Multi-Step Operation ===")
    goal = "Open Notepad and type Welcome to DesktopPilot AI"
    result = await autonomous_pilot.execute_autonomous_goal(goal)
    print("\n--- Pilot Output ---")
    print("Status:", result["status"])
    print("Total Steps:", result["total_steps"])
    print("Summary:", result["final_summary"])
    print("History:")
    for h in result.get("history", []):
        print(" ", h)
    assert result["status"] == "success"
    print("\n[AUTONOMOUS SCREEN AGENT TEST PASSED!]")


if __name__ == "__main__":
    asyncio.run(test_notepad_autonomous_flow())

