# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from core.engine_manager import EngineManager
from core.limiter_engine import LimitRequest


class TestEngineFallback(unittest.TestCase):
    @patch("core.engine_manager.is_admin", return_value=True)
    def test_init_driver_functional_success(self, mock_admin):
        """测试正常管理员与驱动可用时的初始化"""
        with patch("core.windivert_engine.WinDivertEngine.is_driver_functional", return_value=True):
            em = EngineManager()
            self.assertTrue(em.use_windivert)
            self.assertFalse(em.is_downgraded)
            self.assertIn("WinDivert", em.active_engine_display)

    @patch("core.engine_manager.is_admin", return_value=True)
    def test_init_driver_winerror_5_antivirus_fallback(self, mock_admin):
        """测试 WinError 5 (杀软拦截/拒绝访问) 下的自动降级自愈"""
        err = OSError()
        err.winerror = 5

        # 模拟 pydivert 打开时抛出 WinError 5
        with patch("pydivert.WinDivert") as mock_wd:
            mock_wd.side_effect = err
            em = EngineManager()
            self.assertFalse(em.use_windivert)
            self.assertTrue(em.is_downgraded)
            self.assertIn("自动降级", em.active_engine_display)
            diag = em.get_diagnostic_info()
            self.assertTrue(diag["is_downgraded"])
            self.assertEqual(diag["driver_code"], 5)
            self.assertIn("杀毒软件", diag["driver_advice"])

    @patch("core.engine_manager.is_admin", return_value=True)
    def test_init_driver_winerror_1275_policy_fallback(self, mock_admin):
        """测试 WinError 1275 (驱动被阻止/HVCI内核隔离) 下的自动降级自愈"""
        err = OSError()
        err.winerror = 1275

        with patch("pydivert.WinDivert") as mock_wd:
            mock_wd.side_effect = err
            em = EngineManager()
            self.assertFalse(em.use_windivert)
            self.assertTrue(em.is_downgraded)
            diag = em.get_diagnostic_info()
            self.assertEqual(diag["driver_code"], 1275)
            self.assertIn("内核隔离", diag["driver_advice"])

    @patch("core.engine_manager.is_admin", return_value=True)
    def test_runtime_apply_failure_seamless_fallback(self, mock_admin):
        """测试运行时下发失败触发平滑降级并将规则无缝同步至原生引擎"""
        with patch("core.windivert_engine.WinDivertEngine.is_driver_functional", return_value=True):
            em = EngineManager()
            self.assertTrue(em.use_windivert)

            # 模拟在下发时 WinDivert 打开驱动报错
            em.windivert_engine.apply_limits_batch = MagicMock(return_value=(False, "Driver handle closed by Defender", {}))
            em.native_engine.apply_limits_batch = MagicMock(return_value=(True, "Native rules applied", {}))

            reqs = [
                LimitRequest(app_name="game.exe", app_path="C:\\game.exe", upload_speed_type="100kb", download_speed_type="100kb")
            ]
            ok, msg, _ = em.apply_limits_batch(reqs, persist=False)
            self.assertTrue(ok)
            self.assertFalse(em.use_windivert)
            self.assertTrue(em.is_downgraded)
            em.native_engine.apply_limits_batch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
