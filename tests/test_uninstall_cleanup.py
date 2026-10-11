# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from main import run_uninstall_cleanup


class TestUninstallCleanup(unittest.TestCase):
    @patch("core.rules_store.RulesStore.clear")
    @patch("core.limiter_engine.LimiterEngine.remove_all_limits")
    @patch("core.autostart_manager.set_autostart")
    def test_run_uninstall_cleanup_success(self, mock_autostart, mock_limiter, mock_rules):
        """测试卸载清理全流程成功执行"""
        mock_limiter.return_value = (True, "All rules removed", {})
        mock_autostart.return_value = (True, "Autostart removed")

        ok = run_uninstall_cleanup()
        self.assertTrue(ok)
        mock_rules.assert_called_once()
        mock_limiter.assert_called_once()
        mock_autostart.assert_called_once_with(False)

    @patch("core.rules_store.RulesStore.clear")
    @patch("core.limiter_engine.LimiterEngine.remove_all_limits")
    @patch("core.autostart_manager.set_autostart")
    def test_run_uninstall_cleanup_tolerance_on_error(self, mock_autostart, mock_limiter, mock_rules):
        """测试某一步发生异常时其余步骤仍被坚决执行完毕"""
        mock_rules.side_effect = RuntimeError("Disk locked")
        mock_limiter.return_value = (True, "Cleaned", {})

        ok = run_uninstall_cleanup()
        self.assertFalse(ok)
        # 确认即便 RulesStore.clear 抛出异常，LimiterEngine 和 autostart 仍被调用
        mock_limiter.assert_called_once()
        mock_autostart.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
