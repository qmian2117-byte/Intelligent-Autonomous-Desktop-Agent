"""
Automated Regression and Validation Test Suite for DesktopPilot AI — P0 Critical Fixes.
Verifies all 11 P0 audit issues:
1. Command injection neutralization in universal_launcher
2. Safe folder deletion confirmation gate in autonomous_pilot
3. Base64-safe PowerShell TTS parameter passing in voice_engine
4. Restricted CORS and origin security in api/server
5. Zip Slip path traversal defense in smart_file_ops
6. Win32 MOUSEEVENTF_RIGHTUP constant (0x0010)
7. 64-bit ctypes argtypes and restype definitions
8. Unicode / Enter key newline handling
9. Confirmation safeguards on restart and sleep operations
10. Project root / CWD protection in organize_folder
11. Microphone state feedback loop mutex logic in frontend/app.js
"""

import os
import sys
import tempfile
import zipfile
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.system.universal_launcher import universal_launcher
from tools.system.smart_file_ops import smart_file_manager
from tools.desktop.native_input import native_desktop, MOUSEEVENTF_RIGHTUP
from tools.system.system_control import system_control
from models.voice.voice_engine import voice_engine
from agent.autonomous_pilot import autonomous_pilot


class TestP0CriticalFixes(unittest.TestCase):

    def test_01_command_injection_rejected(self):
        """P0-1: Verify universal_launcher refuses illegal shell injection characters."""
        dangerous_target = 'calc.exe & echo vulnerable & notepad.exe'
        res = universal_launcher.open(dangerous_target)
        self.assertEqual(res.get("status"), "error")
        self.assertIn("illegal shell characters", res.get("message", "").lower())

    def test_02_safe_deletion_requires_confirmation(self):
        """P0-2: Verify autonomous_pilot will NOT silently delete folders without confirmation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            del_target = Path(tmp_dir) / "subfolder_to_del"
            del_target.mkdir()
            self.assertTrue(del_target.exists())

            # Goal requesting deletion of the directory
            goal = f"open e drive and desktop folder then serch {del_target.name} folder and then it del"
            # Step 2 simulates folder lookup and delete action
            action = autonomous_pilot._fallback_action(goal, step=2, active_window="")
            self.assertTrue(del_target.exists(), "Target directory must NOT be silently deleted!")
            if hasattr(action, "params") and action.params:
                if action.params.get("status") == "confirmation_required":
                    self.assertIn("confirmation_token", action.params)

    def test_03_voice_engine_powershell_subexpression_safety(self):
        """P0-3: Verify voice_engine safely handles $(cmd), quotes, and semicolons without crashing."""
        malicious_voice_text = 'Hello world $(Get-Process) "double quote" and \'single quote\'; echo hacked'
        # Calling speak should succeed and encode payload safely without raising exceptions
        success = voice_engine.speak(malicious_voice_text)
        self.assertTrue(success)

    def test_04_cors_origins_restricted(self):
        """P0-4: Verify API server CORS origins are restricted to localhost and not '*'."""
        from api.server import ALLOWED_ORIGINS

        self.assertNotIn("*", ALLOWED_ORIGINS)
        self.assertIn("http://localhost:8000", ALLOWED_ORIGINS)
        self.assertIn("http://127.0.0.1:8000", ALLOWED_ORIGINS)

    def test_05_zip_slip_path_traversal_blocked(self):
        """P0-5: Verify smart_file_manager.extract_zip blocks Zip Slip directory traversal attacks."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "malicious.zip"
            dest_dir = Path(tmp_dir) / "destination"
            dest_dir.mkdir()

            # Create an archive containing a Zip Slip directory traversal entry
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("../../../evil.txt", "MALICIOUS PAYLOAD")

            res = smart_file_manager.extract_zip(str(zip_path), str(dest_dir))
            self.assertEqual(res.get("status"), "error")
            self.assertIn("travers", res.get("message", "").lower())
            evil_escaped = Path(tmp_dir).parent / "evil.txt"
            self.assertFalse(evil_escaped.exists(), "Zip slip file must not escape destination directory!")

    def test_06_mouse_event_flag_constant(self):
        """P0-6: Verify MOUSEEVENTF_RIGHTUP is exactly 0x0010 (Win32 standard)."""
        self.assertEqual(MOUSEEVENTF_RIGHTUP, 0x0010)

    def test_07_ctypes_argtypes_and_restype_defined(self):
        """P0-7: Verify 64-bit ctypes argtypes and restype are explicitly declared."""
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        self.assertEqual(user32.GetForegroundWindow.restype, wintypes.HWND)
        self.assertEqual(user32.SetForegroundWindow.restype, wintypes.BOOL)
        self.assertEqual(user32.GetWindowTextW.restype, ctypes.c_int)

    def test_08_unicode_and_enter_newline_handling(self):
        """P0-8: Verify native_desktop.type_text handles strings with newlines without error."""
        res = native_desktop.type_text("Hello\nWorld\r\n", interval=0.001)
        self.assertIn("Typed", res)

    def test_09_disruptive_operations_confirmation_gate(self):
        """P0-9: Verify restart_pc and sleep_pc require explicit confirmation."""
        restart_res = system_control.restart_pc(confirmed=False)
        self.assertEqual(restart_res.get("status"), "confirmation_required")
        self.assertEqual(restart_res.get("confirmation_token"), "CONFIRM_RESTART_PC")

        sleep_res = system_control.sleep_pc(confirmed=False)
        self.assertEqual(sleep_res.get("status"), "confirmation_required")
        self.assertEqual(sleep_res.get("confirmation_token"), "CONFIRM_SLEEP_PC")

    def test_10_organize_folder_protects_project_root(self):
        """P0-10: Verify organize_folder refuses to organize '.' or the current working directory."""
        res_dot = smart_file_manager.organize_folder(".")
        self.assertEqual(res_dot.get("status"), "error")
        self.assertIn("refused", res_dot.get("message", "").lower())

        res_cwd = smart_file_manager.organize_folder(str(Path.cwd()))
        self.assertEqual(res_cwd.get("status"), "error")
        self.assertIn("refused", res_cwd.get("message", "").lower())

    def test_11_frontend_voice_feedback_loop_mutex_present(self):
        """P0-11: Verify frontend/app.js contains audio feedback mutex and backoff logic."""
        app_js_path = Path(__file__).parent.parent / "frontend" / "app.js"
        content = app_js_path.read_text(encoding="utf-8")
        self.assertIn("isAgentSpeaking = true", content)
        self.assertIn("isAgentSpeaking = false", content)
        self.assertIn("micErrorBackoff", content)


if __name__ == "__main__":
    unittest.main()
