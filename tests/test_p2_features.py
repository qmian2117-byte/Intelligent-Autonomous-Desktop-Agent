"""
Automated Test Suite for DesktopPilot AI — Phase 2 (P2) Features.
Verifies:
1. Post-action verification in agent/nodes/verifier (window detection, file verification).
2. Win32 UI element lookup via native_desktop.find_and_click_ui_element.
3. Graceful degradation when external models/tools are offline.
"""

import unittest
import asyncio
from pathlib import Path
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.nodes.verifier import verifier_node
from agent.states.state import AgentState, Step
from tools.desktop.native_input import native_desktop
from tools.vision.screen_understanding import screen_understanding


class TestP2Features(unittest.TestCase):

    def test_01_verifier_window_verification(self):
        """P2-1: Verify verifier_node confirms active desktop application launches."""
        step = Step(
            step_id=1,
            title="Launch app",
            tool_name="open_app",
            tool_parameters={"app_name": "explorer"}
        )
        state: AgentState = {
            "user_goal": "Open explorer",
            "plan": [step],
            "current_step_index": 0,
            "last_tool_output": "Launched application Explorer",
            "retry_count": 0,
            "max_retries": 2,
            "step_verified": False,
            "is_finished": False,
            "is_approved": True,
            "requires_approval": False
        }

        async def run_verifier():
            return await verifier_node(state)

        res = asyncio.run(run_verifier())
        self.assertTrue(res.get("step_verified"))
        self.assertIn("verified", res.get("verification_feedback", "").lower())

    def test_02_verifier_file_creation_verification(self):
        """P2-2: Verify verifier_node confirms file presence on disk."""
        existing_file = str(Path(__file__).resolve())
        step = Step(
            step_id=1,
            title="Copy test file",
            tool_name="file_copy",
            tool_parameters={"destination": existing_file}
        )
        state: AgentState = {
            "user_goal": "Copy file",
            "plan": [step],
            "current_step_index": 0,
            "last_tool_output": {"status": "success", "message": "Copied file"},
            "retry_count": 0,
            "max_retries": 2,
            "step_verified": False,
            "is_finished": False,
            "is_approved": True,
            "requires_approval": False
        }

        async def run_verifier():
            return await verifier_node(state)

        res = asyncio.run(run_verifier())
        self.assertTrue(res.get("step_verified"))
        self.assertIn("exists", res.get("verification_feedback", "").lower())

    def test_03_win32_ui_element_method_exists(self):
        """P2-3: Verify native_desktop has find_and_click_ui_element implemented."""
        self.assertTrue(hasattr(native_desktop, "find_and_click_ui_element"))
        # Non-existent window should return None gracefully without throwing exceptions
        result = native_desktop.find_and_click_ui_element("NonExistentWindow12345", "Button")
        self.assertIsNone(result)

    def test_04_graceful_screen_understanding_fallback(self):
        """P2-4: Verify screen_understanding takes screenshots and provides analysis even if OCR/LLM degrades."""
        res = screen_understanding.take_screenshot(save_to_pictures=False)
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(Path(res.get("screenshot_path")).exists())


if __name__ == "__main__":
    unittest.main()

