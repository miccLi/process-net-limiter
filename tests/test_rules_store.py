# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from core.limiter_engine import LimitRequest
from core.rules_store import RulesStore, StoredRule
from core.engine_manager import EngineManager


class TestRulesStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.rules_path = os.path.join(self.temp_dir.name, "test_rules.json")
        self.store = RulesStore(filepath=self.rules_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_rule(self):
        """测试：持久化存储单条与批量规则并准确回读"""
        req = LimitRequest(
            app_name="thunder.exe",
            app_path="C:\\Program Files\\Thunder\\Thunder.exe",
            upload_speed_type="100kb",
            download_speed_type="1000kb",
            custom_upload_val=0,
            custom_upload_unit="KB/s",
            custom_download_val=0,
            custom_download_unit="KB/s"
        )
        self.store.save_request(req)

        # 重新创建 Store 实例读取文件
        new_store = RulesStore(filepath=self.rules_path)
        rule = new_store.get_rule("thunder.exe")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.app_name, "thunder.exe")
        self.assertEqual(rule.upload_speed_type, "100kb")
        self.assertEqual(rule.download_speed_type, "1000kb")

    def test_remove_and_clear_rules(self):
        """测试：删除单条/批量与一键清空规则"""
        req1 = LimitRequest(app_name="app1.exe", app_path="C:\\app1.exe", upload_speed_type="1kb", download_speed_type="none")
        req2 = LimitRequest(app_name="app2.exe", app_path="C:\\app2.exe", upload_speed_type="block", download_speed_type="block")
        self.store.save_requests_batch([req1, req2])
        self.assertEqual(len(self.store.get_all_rules()), 2)

        self.store.remove_rule("app1.exe")
        self.assertIsNone(self.store.get_rule("app1.exe"))
        self.assertIsNotNone(self.store.get_rule("app2.exe"))

        self.store.clear()
        self.assertEqual(len(self.store.get_all_rules()), 0)

    def test_path_drift_self_healing(self):
        """测试：进程版本升级导致路径漂移时，自动校准自愈并生成更新后的下发对象"""
        old_path = "C:\\Google\\Chrome\\128.0.0\\chrome.exe"
        new_path = "C:\\Google\\Chrome\\129.0.0\\chrome.exe"

        req = LimitRequest(
            app_name="chrome.exe",
            app_path=old_path,
            upload_speed_type="100kb",
            download_speed_type="none"
        )
        self.store.save_request(req)

        # 模拟当前系统中运行的 chrome.exe 是 129.0 新版路径
        running_apps = {"chrome.exe": new_path}
        requests_to_apply, healed_count = self.store.reconcile_and_heal(running_apps)

        self.assertEqual(healed_count, 1)
        self.assertEqual(len(requests_to_apply), 1)
        self.assertEqual(requests_to_apply[0].app_path, new_path)

        # 磁盘上记录的路径也应当被同步自愈更新
        new_store = RulesStore(filepath=self.rules_path)
        self.assertEqual(new_store.get_rule("chrome.exe").app_path, new_path)

    def test_engine_manager_auto_rebind(self):
        """测试：EngineManager 协同自愈重载持久化规则"""
        req = LimitRequest(app_name="game.exe", app_path="D:\\game.exe", upload_speed_type="1kb", download_speed_type="none")
        self.store.save_request(req)

        engine = EngineManager(rules_store=self.store)
        engine.apply_limits_batch = MagicMock(return_value=(True, "OK", {}))

        running_apps = {"game.exe": "D:\\game.exe"}
        rebound_count, healed_count = engine.auto_rebind_persistent_rules(running_apps)

        self.assertEqual(rebound_count, 1)
        self.assertEqual(healed_count, 0)
    def test_corrupt_json_quarantine_backup(self):
        """测试：遭遇损坏 JSON 时自动隔离备份为 .corrupt.<ts>.bak 并安全返回空字典"""
        with open(self.rules_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json syntax ... ")

        store = RulesStore(filepath=self.rules_path)
        self.assertEqual(len(store.get_all_rules()), 0)

        # 检查是否生成了 .corrupt.*.bak 文件
        parent_dir = os.path.dirname(self.rules_path)
        bak_files = [f for f in os.listdir(parent_dir) if ".corrupt." in f and f.endswith(".bak")]
        self.assertTrue(len(bak_files) >= 1)

    def test_atomic_save_tmp_cleanup(self):
        """测试：原子保存过程中 .tmp 临时文件在完成后被重命名替换，不留垃圾文件"""
        req = LimitRequest(app_name="app.exe", app_path="C:\\app.exe", upload_speed_type="100kb", download_speed_type="none")
        self.store.save_request(req)
        
        parent_dir = os.path.dirname(self.rules_path)
        tmp_files = [f for f in os.listdir(parent_dir) if f.endswith(".tmp")]
        self.assertEqual(len(tmp_files), 0)
        self.assertTrue(os.path.exists(self.rules_path))


if __name__ == "__main__":
    unittest.main()
