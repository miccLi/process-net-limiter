# -*- coding: utf-8 -*-
import unittest
from core.process_scanner import (
    classify_process, scan_and_group_processes, ProcessCategory, KNOWN_FAMILIES
)
from core.limiter_engine import PolicyStatus

class TestProcessScanner(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify_process("thunder.exe", ""), ProcessCategory.DOWNLOADER)
        self.assertEqual(classify_process("baidunetdisk.exe", ""), ProcessCategory.CLOUD_DRIVE)
        self.assertEqual(classify_process("onedrive.exe", ""), ProcessCategory.CLOUD_DRIVE)
        self.assertEqual(classify_process("steam.exe", ""), ProcessCategory.GAME)
        self.assertEqual(classify_process("cs2.exe", ""), ProcessCategory.GAME)
        self.assertEqual(classify_process("chrome.exe", ""), ProcessCategory.BROWSER_SOCIAL)
        self.assertEqual(classify_process("randomapp.exe", ""), ProcessCategory.OTHER)

    def test_known_families(self):
        self.assertIn("steamwebhelper.exe", KNOWN_FAMILIES)
        fam_id, fam_name = KNOWN_FAMILIES["steamwebhelper.exe"]
        self.assertEqual(fam_id, "Steam")
        self.assertIn("filesynchelper.exe", KNOWN_FAMILIES)
        fam_id, fam_name = KNOWN_FAMILIES["filesynchelper.exe"]
        self.assertEqual(fam_id, "OneDrive")

    def test_scan_and_group_structure(self):
        mock_policies = {
            "onedrive.exe": PolicyStatus(app_name="OneDrive.exe", upload_bps=8192, download_bps=8192, summary="1 KB/s")
        }
        families = scan_and_group_processes(mock_policies)
        self.assertIsInstance(families, list)
        self.assertGreater(len(families), 0)

        # Check that onedrive family is marked as limited and placed at the top (sort_priority == -1)
        onedrive_fam = next((f for f in families if f.family_id.lower() == "onedrive"), None)
        if onedrive_fam:
            self.assertTrue(onedrive_fam.is_limited)
            self.assertEqual(onedrive_fam.sort_priority, -1)
            self.assertEqual(families[0].sort_priority, -1)

if __name__ == "__main__":
    unittest.main()
