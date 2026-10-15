# -*- coding: utf-8 -*-
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPixmap

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from core.autostart_manager import is_autostart_enabled, set_autostart, TASK_NAME
from ui.system_tray import create_tray_pixmap, SystemTrayManager


class TestAutostartAndTray(unittest.TestCase):
    @patch("subprocess.run")
    def test_is_autostart_enabled_true(self, mock_run):
        """测试：schtasks 查询成功返回已注册"""
        mock_run.return_value = MagicMock(returncode=0, stdout="TaskName", stderr="")
        self.assertTrue(is_autostart_enabled())
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("/query", args)
        self.assertIn(TASK_NAME, args)

    @patch("subprocess.run")
    def test_is_autostart_enabled_false(self, mock_run):
        """测试：schtasks 查询失败返回未注册"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ERROR")
        self.assertFalse(is_autostart_enabled())

    @patch("subprocess.run")
    def test_set_autostart_enable_success(self, mock_run):
        """测试：成功创建计划任务"""
        mock_run.return_value = MagicMock(returncode=0, stdout="SUCCESS", stderr="")
        ok, msg = set_autostart(True)
        self.assertTrue(ok)
        first_args = mock_run.call_args_list[0][0][0]
        self.assertIn("/create", first_args)
        self.assertIn("highest", first_args)
        self.assertIn("onlogon", first_args)

    @patch("subprocess.run")
    def test_set_autostart_disable_success(self, mock_run):
        """测试：成功删除计划任务"""
        mock_run.return_value = MagicMock(returncode=0, stdout="SUCCESS", stderr="")
        ok, msg = set_autostart(False)
        self.assertTrue(ok)
        args = mock_run.call_args[0][0]
        self.assertIn("/delete", args)

    def test_create_tray_pixmap(self):
        """测试：动态矢量托盘图标生成有效图像"""
        pix = create_tray_pixmap(64)
        self.assertIsInstance(pix, QPixmap)
        self.assertFalse(pix.isNull())
        self.assertEqual(pix.width(), 64)
        self.assertEqual(pix.height(), 64)

    def test_tray_manager_initialization_and_toggle(self):
        """测试：SystemTrayManager 菜单初始化与显示切换"""
        mock_window = MagicMock()
        mock_window.isVisible.return_value = True
        mock_window.engine.active_engine_display = "🚀 WinDivert"

        tray = SystemTrayManager(mock_window)
        self.assertIsNotNone(tray.menu)
        self.assertFalse(tray.tray_icon.isNull())

        # 切换窗口显示状态
        tray._toggle_window_visibility()
        mock_window.hide.assert_called_once()

        mock_window.isVisible.return_value = False
        tray._toggle_window_visibility()
        mock_window.show.assert_called_once()

    def test_tray_emergency_restore_signal(self):
        """测试：点击托盘紧急恢复发送信号"""
        mock_window = MagicMock()
        tray = SystemTrayManager(mock_window)

        received = []
        tray.restoreAllRequested.connect(lambda: received.append(True))
        tray.action_restore.trigger()

        self.assertEqual(received, [True])

    @patch("core.autostart_manager.is_autostart_enabled", return_value=False)
    @patch("subprocess.run")
    def test_set_autostart_disable_when_not_exist(self, mock_run, mock_is_enabled):
        """测试：在非英文系统下删除不存在的计划任务时依然能够安全判定为成功"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="错误: 系统找不到指定的文件。")
        ok, msg = set_autostart(False)
        self.assertTrue(ok)
        self.assertEqual(msg, "Success")

    @patch("ui.system_tray.is_autostart_enabled")
    def test_tray_about_to_show_updates_state(self, mock_is_enabled):
        """测试：托盘菜单弹出前 _on_menu_about_to_show 正确同步自启与窗口显示状态"""
        mock_is_enabled.return_value = True
        mock_window = MagicMock()
        mock_window.isVisible.return_value = False
        mock_window.engine.active_engine_display = "EngineTest"

        tray = SystemTrayManager(mock_window)
        # 初始状态
        tray.action_autostart.setChecked(False)

        # 触发菜单即将展现事件
        tray._on_menu_about_to_show()
        self.assertTrue(tray.action_autostart.isChecked(), "应自动校准自启勾选状态")
        self.assertIn("EngineTest", tray.action_engine.text())

    def test_build_elevation_args(self):
        """测试：UAC 参数构建在源码与打包模式下正确分流"""
        from core.uac_manager import _build_elevation_args

        with patch.object(sys, "argv", ["main.py", "--minimized", "--no-elevate"]):
            with patch.object(sys, "frozen", False, create=True):
                target_exe, args_str, script_dir = _build_elevation_args()
                self.assertIn("--minimized", args_str)
                self.assertNotIn("--no-elevate", args_str)
                self.assertTrue(args_str.startswith('"'))

            with patch.object(sys, "frozen", True, create=True):
                target_exe, args_str, script_dir = _build_elevation_args()
                self.assertEqual(args_str, "--minimized")


if __name__ == "__main__":
    unittest.main()
