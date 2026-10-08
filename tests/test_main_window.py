# -*- coding: utf-8 -*-
import sys
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QCloseEvent

from ui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestMainWindow(unittest.TestCase):
    @patch("ui.main_window.EngineManager")
    @patch("ui.main_window.scan_and_group_processes")
    def setUp(self, mock_scan, mock_engine_cls):
        self.mock_engine = MagicMock()
        self.mock_engine.active_engine_name = "WINDIVERT"
        self.mock_engine.active_engine_display = "🚀 WinDivert"
        self.mock_engine.get_active_policies.return_value = {}
        mock_engine_cls.return_value = self.mock_engine
        mock_scan.return_value = []

        self.window = MainWindow()

    def test_filter_chips_contain_limited(self):
        """测试：主界面分类筛选芯片中包含'LIMITED'和'BROWSER_SOCIAL'"""
        buttons = self.window.filter_group.buttons()
        # 应该有 6 个按钮: ALL, LIMITED, DOWNLOADER, CLOUD_DRIVE, GAME, BROWSER_SOCIAL
        self.assertEqual(len(buttons), 6)

    def test_dynamic_engine_tip(self):
        """测试：底部说明提示文本根据活跃引擎类型动态调整"""
        # 1. WinDivert 模式
        self.mock_engine.active_engine_name = "WINDIVERT"
        self.mock_engine.active_engine_display = "🚀 内核驱动整形 (WinDivert 硬件级精准)"
        self.window._update_engine_status_and_tip()
        self.assertIn("WinDivert 内核级流量整形引擎", self.window.tip_label.text())

        # 2. 原生 Native 模式
        self.mock_engine.active_engine_name = "NATIVE"
        self.mock_engine.active_engine_display = "🛡️ 原生组策略引擎"
        self.window._update_engine_status_and_tip()
        self.assertIn("Windows 原生系统策略引擎模式", self.window.tip_label.text())

    def test_close_event_stops_engine_and_timers(self):
        """测试：窗口关闭时正确停止定时器并回收引擎资源"""
        self.window.scan_timer.start(5000)
        self.assertTrue(self.window.scan_timer.isActive())

        event = QCloseEvent()
        self.window.closeEvent(event)

        self.assertFalse(self.window.scan_timer.isActive())
        self.mock_engine.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
