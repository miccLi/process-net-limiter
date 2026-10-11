# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
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

    def tearDown(self):
        if hasattr(self, "window") and self.window:
            self.window._force_quit = True
            event = QCloseEvent()
            self.window.closeEvent(event)

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
        self.mock_engine.is_downgraded = False
        self.mock_engine.diagnostic = None
        self.window._update_engine_status_and_tip()
        self.assertIn("Windows 原生系统策略引擎模式", self.window.tip_label.text())

    def test_dynamic_engine_tip_downgraded(self):
        """测试：驱动受阻自动降级时的黄色警告与提示文案"""
        self.mock_engine.active_engine_name = "NATIVE"
        self.mock_engine.is_downgraded = True
        self.mock_engine.downgrade_reason = "杀毒软件拦截"
        self.window._update_engine_status_and_tip()
        self.assertIn("驱动加载受阻", self.window.tip_label.text())
        self.assertIn("杀毒软件拦截", self.window.tip_label.text())

    def test_dynamic_engine_tip_accelerator_environment(self):
        """测试：检测到加速器/VPN虚拟网卡时的透传保护提示"""
        from core.network_compat import NetworkDiagnostic
        self.mock_engine.active_engine_name = "WINDIVERT"
        self.mock_engine.is_downgraded = False
        self.mock_engine.diagnostic = NetworkDiagnostic(is_accelerator_environment=True)
        self.window._update_engine_status_and_tip()
        self.assertIn("网络加速器/VPN", self.window.tip_label.text())


    def test_close_event_stops_engine_and_timers(self):
        """测试：显式退出窗口时正确停止定时器并回收引擎资源"""
        self.window.scan_timer.start(5000)
        self.assertTrue(self.window.scan_timer.isActive())

        self.window._force_quit = True
        event = QCloseEvent()
        self.window.closeEvent(event)

        self.assertFalse(self.window.scan_timer.isActive())
        self.mock_engine.stop.assert_called_once()

    def test_close_event_minimizes_to_tray_by_default(self):
        """测试：默认点击关闭按钮时最小化隐藏到系统托盘，不释放引擎资源"""
        self.window.show()
        self.window._force_quit = False
        event = QCloseEvent()
        self.window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertFalse(self.window.isVisible())
        self.mock_engine.stop.assert_not_called()




if __name__ == "__main__":
    unittest.main()
