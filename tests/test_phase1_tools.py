"""
Unit and integration tests for Phase 1 DesktopPilot AI Tools:
1. Universal "Open Anything" Launcher
2. Search Files & Folders
3. Clipboard AI
4. Windows System Control
"""

import unittest
from tools.system.universal_launcher import universal_launcher
from tools.system.file_search import file_search_tool
from tools.system.clipboard_ai import clipboard_ai
from tools.system.system_control import system_control
from tools.registry import tool_registry


class TestPhase1Tools(unittest.TestCase):

    def test_01_registry_registration(self):
        """Verify all new Phase 1 tools are registered in the global ToolRegistry."""
        required_tools = [
            "open_anything",
            "search_files",
            "preview_file",
            "copy_file_path",
            "reveal_file_in_explorer",
            "clipboard_summarize",
            "clipboard_translate",
            "clipboard_rewrite",
            "clipboard_format_markdown",
            "volume_up",
            "volume_down",
            "mute_volume",
            "set_brightness",
            "empty_recycle_bin",
            "lock_pc",
            "schedule_shutdown",
            "cancel_shutdown",
            "get_system_metrics"
        ]
        for tool_name in required_tools:
            self.assertIn(tool_name, tool_registry._tools, f"Tool '{tool_name}' missing in registry.")
            self.assertIn(tool_name, tool_registry._schemas, f"Schema for '{tool_name}' missing.")

    def test_02_clipboard_io(self):
        """Verify reading and writing to the Windows clipboard."""
        test_text = "DesktopPilot AI - Phase 1 Clipboard Verification"
        ok = clipboard_ai.set_clipboard_text(test_text)
        self.assertTrue(ok)
        read_back = clipboard_ai.get_clipboard_text()
        self.assertEqual(read_back, test_text)

    def test_03_clipboard_markdown_format(self):
        """Verify converting list/tabular text into Markdown in clipboard."""
        raw_list = "Task 1\nTask 2\nTask 3"
        clipboard_ai.set_clipboard_text(raw_list)
        res = clipboard_ai.format_as_markdown()
        self.assertEqual(res["status"], "success")
        self.assertIn("- Task 1", res["markdown"])

    def test_04_file_search_and_preview(self):
        """Verify searching and previewing files in the repository."""
        res = file_search_tool.search_files(query="settings", search_dir=".", extension="py")
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["total_found"], 0)
        
        target_path = res["files"][0]["path"]
        preview_res = file_search_tool.preview_file(target_path, max_lines=5)
        self.assertEqual(preview_res["status"], "success")
        self.assertTrue(len(preview_res["preview"]) > 0)

    def test_05_system_control_safe_operations(self):
        """Verify system control calls execute without errors."""
        vol_up = system_control.volume_up(steps=2)
        self.assertEqual(vol_up["status"], "success")

        vol_down = system_control.volume_down(steps=2)
        self.assertEqual(vol_down["status"], "success")

        mute_res = system_control.toggle_mute()
        self.assertEqual(mute_res["status"], "success")

        metrics = system_control.get_system_battery_and_memory()
        self.assertEqual(metrics["status"], "success")
        self.assertIn("TotalRAM_GB", metrics["system_metrics"])

        # Test schedule and immediate cancellation
        sched = system_control.schedule_shutdown(minutes=120)
        self.assertEqual(sched["status"], "success")
        cancel = system_control.cancel_shutdown()
        self.assertEqual(cancel["status"], "success")

    def test_06_universal_launcher_resolution(self):
        """Verify resolution logic for files, folders, and popular targets."""
        # Folder test
        downloads_res = universal_launcher.open("downloads")
        self.assertEqual(downloads_res["status"], "success")
        self.assertEqual(downloads_res["category"], "folder")


if __name__ == "__main__":
    unittest.main()

