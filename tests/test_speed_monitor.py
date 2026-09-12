# -*- coding: utf-8 -*-
import unittest
from core.speed_monitor import SpeedMonitor, ProcessSpeed

class TestSpeedMonitor(unittest.TestCase):
    def test_format_speed(self):
        self.assertEqual(SpeedMonitor.format_speed(0), "—")
        self.assertEqual(SpeedMonitor.format_speed(5), "—")
        self.assertEqual(SpeedMonitor.format_speed(500), "500 B/s")
        self.assertEqual(SpeedMonitor.format_speed(1024), "1.0 KB/s")
        self.assertEqual(SpeedMonitor.format_speed(100 * 1024), "100.0 KB/s")
        self.assertEqual(SpeedMonitor.format_speed(1.5 * 1024 * 1024), "1.50 MB/s")
        self.assertEqual(SpeedMonitor.format_speed(2.5 * 1024 * 1024 * 1024), "2.50 GB/s")

    def test_sampling_instantiation(self):
        monitor = SpeedMonitor()
        speeds = monitor.update_and_get_speeds()
        self.assertIsInstance(speeds, dict)

if __name__ == "__main__":
    unittest.main()
