# -*- coding: utf-8 -*-
import unittest
from core.limiter_engine import LimiterEngine, LimitRequest, ASSOCIATED_PROCESSES

class TestLimiterEngine(unittest.TestCase):
    def setUp(self):
        self.engine = LimiterEngine()

    def test_speed_conversion(self):
        # 1 KB/s -> 8192 bps
        self.assertEqual(self.engine.speed_str_to_bps("1kb"), 8192)
        # 100 KB/s -> 819200 bps
        self.assertEqual(self.engine.speed_str_to_bps("100kb"), 819200)
        # 1000 KB/s -> 8192000 bps
        self.assertEqual(self.engine.speed_str_to_bps("1000kb"), 8192000)
        # block -> -1
        self.assertEqual(self.engine.speed_str_to_bps("block"), -1)
        # none -> 0
        self.assertEqual(self.engine.speed_str_to_bps("none"), 0)
        # custom: 500 KB/s
        self.assertEqual(self.engine.speed_str_to_bps("custom", 500, "KB/s"), 500 * 1024 * 8)
        # custom: 2 MB/s
        self.assertEqual(self.engine.speed_str_to_bps("custom", 2, "MB/s"), 2 * 1024 * 1024 * 8)

    def test_associated_processes(self):
        self.assertIn("steam.exe", ASSOCIATED_PROCESSES)
        self.assertIn("steamwebhelper.exe", ASSOCIATED_PROCESSES["steam.exe"])
        self.assertIn("baidunetdisk.exe", ASSOCIATED_PROCESSES)
        self.assertIn("baidunetdiskhost.exe", ASSOCIATED_PROCESSES["baidunetdisk.exe"])
        self.assertIn("thunder.exe", ASSOCIATED_PROCESSES)
        self.assertIn("downloadsdkserver.exe", ASSOCIATED_PROCESSES["thunder.exe"])

if __name__ == "__main__":
    unittest.main()
