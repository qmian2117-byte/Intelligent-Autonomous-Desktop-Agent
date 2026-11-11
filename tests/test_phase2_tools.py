"""
Unit and integration tests for Phase 2 DesktopPilot AI Tools:
1. Smart File Management (Copy, Rename, Zip, Extract, Organize)
2. Download Manager
3. Decision Engine Routing for Phase 2
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from tools.system.smart_file_ops import smart_file_manager
from tools.system.download_manager import download_manager
from agent.decision_engine import decision_engine
from tools.registry import tool_registry


class TestPhase2Tools(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="dp_test_phase2_"))
        # Create dummy files
        (self.test_dir / "sample_doc.pdf").write_text("dummy pdf", encoding="utf-8")
        (self.test_dir / "sample_img.png").write_text("dummy png", encoding="utf-8")
        (self.test_dir / "sample_script.py").write_text("print('hello')", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_zip_and_extract(self):
        """Test compressing directory to ZIP and extracting it."""
        zip_res = smart_file_manager.compress_to_zip(str(self.test_dir))
        self.assertEqual(zip_res["status"], "success")
        zip_path = Path(zip_res["zip_path"])
        self.assertTrue(zip_path.exists())

        # Extract
        extract_dest = self.test_dir.parent / "extracted_out"
        extract_res = smart_file_manager.extract_zip(str(zip_path), str(extract_dest))
        self.assertEqual(extract_res["status"], "success")
        self.assertTrue((extract_dest / "sample_doc.pdf").exists())

        # Cleanup
        shutil.rmtree(extract_dest, ignore_errors=True)
        zip_path.unlink(missing_ok=True)

    def test_02_organize_folder(self):
        """Test auto-organizing files into categorized folders."""
        org_res = smart_file_manager.organize_folder(str(self.test_dir))
        self.assertEqual(org_res["status"], "success")
        self.assertEqual(org_res["total_organized"], 3)
        self.assertTrue((self.test_dir / "Documents" / "sample_doc.pdf").exists())
        self.assertTrue((self.test_dir / "Images" / "sample_img.png").exists())
        self.assertTrue((self.test_dir / "Code" / "sample_script.py").exists())

    def test_03_copy_and_rename(self):
        """Test copying and renaming files."""
        src_file = self.test_dir / "sample_doc.pdf"
        copy_dest = self.test_dir / "copied_doc.pdf"
        
        copy_res = smart_file_manager.copy_item(str(src_file), str(copy_dest))
        self.assertEqual(copy_res["status"], "success")
        self.assertTrue(copy_dest.exists())

        rename_res = smart_file_manager.rename_item(str(copy_dest), "renamed_doc.pdf")
        self.assertEqual(rename_res["status"], "success")
        self.assertTrue((self.test_dir / "renamed_doc.pdf").exists())

    def test_04_phase2_registry(self):
        """Verify Phase 2 tools are present in registry."""
        tools = ["file_copy", "file_move", "file_rename", "file_compress_zip", "file_extract_zip", "folder_auto_organize", "download_file", "organize_downloads"]
        for t in tools:
            self.assertIn(t, tool_registry._tools)


if __name__ == "__main__":
    unittest.main()
