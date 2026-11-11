"""
Unit Tests for Phase 3 Tools of DesktopPilot AI:
- Task 5: Browser Automation (web_search, open_multiple_tabs)
- Task 6: Screenshot & Screen Understanding (take_screenshot, extract_text_from_screen, explain_screen)
- Task 8: AI Writing Assistant (improve_text_in_app)
- Decision Engine routing for Phase 3 prompts
"""

import unittest
import asyncio
from tools.vision.screen_understanding import screen_understanding
from tools.system.writing_assistant import writing_assistant
from tools.system.clipboard_ai import clipboard_ai
from agent.decision_engine import decision_engine


class TestPhase3Tools(unittest.TestCase):

    def test_1_screenshot_and_ocr(self):
        res = screen_understanding.take_screenshot(save_to_pictures=False)
        self.assertEqual(res["status"], "success")
        self.assertTrue(len(res["path"]) > 0)

        ocr_res = screen_understanding.extract_text_from_screen()
        self.assertEqual(ocr_res["status"], "success")
        self.assertIn("active_window", ocr_res)

    def test_2_explain_screen(self):
        explain_res = asyncio.run(screen_understanding.explain_screen())
        self.assertEqual(explain_res["status"], "success")
        self.assertIn("explanation", explain_res)

    def test_3_writing_assistant(self):
        clipboard_ai.set_clipboard_text("i needs help with this code asap")
        res = asyncio.run(writing_assistant.improve_text_in_app(action="professional", auto_paste=False))
        self.assertEqual(res["status"], "success")
        self.assertTrue(len(res["output_text"]) > 0)

    def test_4_decision_engine_phase3(self):
        d1 = asyncio.run(decision_engine.decide_action("take a screenshot"))
        self.assertEqual(d1.tool_name, "take_screenshot")

        d2 = asyncio.run(decision_engine.decide_action("explain screen"))
        self.assertEqual(d2.tool_name, "explain_screen")

        d3 = asyncio.run(decision_engine.decide_action("extract text from screen"))
        self.assertEqual(d3.tool_name, "extract_screen_text")

        # Power & Tracker & Slack & E Drive routing
        d4 = asyncio.run(decision_engine.decide_action("sleep computer"))
        self.assertEqual(d4.tool_name, "sleep_pc")

        d5 = asyncio.run(decision_engine.decide_action("restrart computer"))
        self.assertEqual(d5.tool_name, "restart_pc")

        d6 = asyncio.run(decision_engine.decide_action("shutdown computer"))
        self.assertEqual(d6.tool_name, "schedule_shutdown")

        d7 = asyncio.run(decision_engine.decide_action("open limerox"))
        self.assertEqual(d7.tool_name, "open_anything")

        d8 = asyncio.run(decision_engine.decide_action("open limerox and start tracking"))
        self.assertEqual(d8.tool_name, "autonomous_screen_pilot")

        d9 = asyncio.run(decision_engine.decide_action("open slack"))
        self.assertEqual(d9.tool_name, "open_anything")

        d10 = asyncio.run(decision_engine.decide_action("open E DRIVE IN MY PC"))
        self.assertEqual(d10.tool_name, "open_anything")


if __name__ == "__main__":
    unittest.main()

