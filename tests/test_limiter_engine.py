from unittest.mock import patch
import unittest
import os
from core.limiter_engine import LimiterEngine, LimitRequest, ASSOCIATED_PROCESSES
from core.process_scanner import SYSTEM_PROTECTED_EXES

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
        self.assertIn("baidunetdiskunite.exe", ASSOCIATED_PROCESSES["baidunetdisk.exe"])
        self.assertIn("thunder.exe", ASSOCIATED_PROCESSES)
        self.assertIn("downloadsdkserver.exe", ASSOCIATED_PROCESSES["thunder.exe"])

    @patch("core.limiter_engine.run_powershell_script")
    def test_empty_path_block_safety(self, mock_run_ps):
        """测试：可执行文件路径为空或不存在时，严禁下发不带 -Program 的全局防火墙规则"""
        mock_run_ps.return_value = (True, "---POLICY_JSON_START---{}---POLICY_JSON_END---")
        
        req = LimitRequest(
            app_name="phantom_app.exe",
            app_path="C:\\nonexistent\\phantom_app.exe",
            upload_speed_type="block",
            download_speed_type="block"
        )
        ok, msg, _ = self.engine.apply_limits_batch([req])
        self.assertTrue(ok)
        
        # 捕获生成的 powershell 脚本
        script_called = mock_run_ps.call_args[0][0]
        # 确认绝不存在不带 -Program 的全局 New-NetFirewallRule
        self.assertNotIn("New-NetFirewallRule", script_called)

    @patch("core.limiter_engine.run_powershell_script")
    def test_system_protected_process_skipped(self, mock_run_ps):
        """测试：系统核心保护进程（如 svchost.exe）必须被安全拦截，不生成任何限制规则"""
        mock_run_ps.return_value = (True, "---POLICY_JSON_START---{}---POLICY_JSON_END---")
        
        req = LimitRequest(
            app_name="svchost.exe",
            app_path="C:\\Windows\\System32\\svchost.exe",
            upload_speed_type="100kb",
            download_speed_type="100kb"
        )
        ok, msg, _ = self.engine.apply_limits_batch([req])
        self.assertTrue(ok)
        # 因为被保护过滤，没有任何命令被发送给 powershell
        mock_run_ps.assert_not_called()

    @patch("core.limiter_engine.run_powershell_script")
    @patch("os.path.exists")
    def test_powershell_quote_escaping(self, mock_exists, mock_run_ps):
        """测试：带单引号的程序名称和路径能被正确转义，杜绝命令注入"""
        mock_exists.return_value = True
        mock_run_ps.return_value = (True, "---POLICY_JSON_START---{}---POLICY_JSON_END---")
        
        req = LimitRequest(
            app_name="test'app.exe",
            app_path="C:\\Program Files\\test'dir\\test'app.exe",
            upload_speed_type="block",
            download_speed_type="block"
        )
        ok, msg, _ = self.engine.apply_limits_batch([req])
        self.assertTrue(ok)
        
        script_called = mock_run_ps.call_args[0][0]
        # 确认单引号被转义为 ''
        self.assertIn("test''app.exe", script_called)
        self.assertIn("test''dir", script_called)
        # 且带有明确的 -Program
        self.assertIn("-Program 'C:\\Program Files\\test''dir\\test''app.exe'", script_called)

if __name__ == "__main__":
    unittest.main()
