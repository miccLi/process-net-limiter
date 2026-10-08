# -*- coding: utf-8 -*-
import unittest
from core.speed_utils import speed_str_to_bps, format_speed_display, format_policy_summary


class TestSpeedUtils(unittest.TestCase):
    def test_speed_str_to_bps_presets(self):
        """测试预设档位转换"""
        self.assertEqual(speed_str_to_bps("block"), -1)
        self.assertEqual(speed_str_to_bps("1kb"), 8192)
        self.assertEqual(speed_str_to_bps("100kb"), 819200)
        self.assertEqual(speed_str_to_bps("1000kb"), 8192000)
        self.assertEqual(speed_str_to_bps("none"), 0)
        self.assertEqual(speed_str_to_bps("unknown"), 0)

    def test_speed_str_to_bps_custom(self):
        """测试自定义速度档位转换与各单位换算"""
        # 500 KB/s
        self.assertEqual(speed_str_to_bps("custom", 500, "KB/s"), 500 * 1024 * 8)
        # 5 MB/s
        self.assertEqual(speed_str_to_bps("custom", 5, "MB/s"), 5 * 1024 * 1024 * 8)
        # 1 GB/s
        self.assertEqual(speed_str_to_bps("custom", 1, "GB/s"), 1024 * 1024 * 1024 * 8)
        # 最低钳位保护 (1000 bps)
        self.assertEqual(speed_str_to_bps("custom", 0.0001, "KB/s"), 1000)

    def test_format_speed_display(self):
        """测试自适应人类可读速度格式化"""
        self.assertEqual(format_speed_display(0), "不限")
        self.assertEqual(format_speed_display(-1), "不限")
        self.assertEqual(format_speed_display(800), "100 B/s")
        self.assertEqual(format_speed_display(8192), "1 KB/s")
        self.assertEqual(format_speed_display(819200), "100 KB/s")
        self.assertEqual(format_speed_display(8192000), "1000 KB/s")
        self.assertEqual(format_speed_display(8 * 1024 * 1024), "1 MB/s")
        self.assertEqual(format_speed_display(int(2.5 * 1024 * 1024 * 8)), "2.5 MB/s")
        self.assertEqual(format_speed_display(8 * 1024 * 1024 * 1024), "1 GB/s")

    def test_format_policy_summary(self):
        """测试策略描述文本拼接"""
        self.assertEqual(format_policy_summary(True), "⛔ 完全断网")
        self.assertEqual(format_policy_summary(True, block_tag="⛔ 阻断"), "⛔ 阻断")
        self.assertEqual(format_policy_summary(False, 0, 0), "正常")
        self.assertEqual(format_policy_summary(False, 8192, 0), "上: 1 KB/s")
        self.assertEqual(format_policy_summary(False, 0, 819200), "下: 100 KB/s")
        self.assertEqual(format_policy_summary(False, 8192, 819200), "上: 1 KB/s | 下: 100 KB/s")


if __name__ == "__main__":
    unittest.main()
