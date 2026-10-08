# -*- coding: utf-8 -*-
import sys
import unittest
from PyQt5.QtWidgets import QApplication

from ui.process_tree import ProcessTreeWidget
from core.process_scanner import ProcessFamily, ProcessItem, ProcessCategory

# 确保 QApplication 实例存在 (单例)
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestProcessTreeWidget(unittest.TestCase):
    def setUp(self):
        self.tree = ProcessTreeWidget()

        # 构造模拟家族数据
        self.normal_item = ProcessItem(
            pid=1001,
            name="normal_app.exe",
            exe_path="C:\\Apps\\normal_app.exe",
            category=ProcessCategory.DOWNLOADER,
            connections_count=2,
            is_limited=False,
            limit_summary="正常",
            sort_priority=1,
            is_protected=False
        )
        self.normal_fam = ProcessFamily(
            family_id="normal_app",
            display_name="Normal App",
            category=ProcessCategory.DOWNLOADER,
            children=[self.normal_item],
            is_protected=False
        )

        self.sys_item = ProcessItem(
            pid=4,
            name="svchost.exe",
            exe_path="C:\\Windows\\System32\\svchost.exe",
            category=ProcessCategory.OTHER,
            connections_count=10,
            is_limited=False,
            limit_summary="正常",
            sort_priority=5,
            is_protected=True
        )
        self.sys_fam = ProcessFamily(
            family_id="svchost",
            display_name="svchost",
            category=ProcessCategory.OTHER,
            children=[self.sys_item],
            is_protected=True
        )

        self.game_item = ProcessItem(
            pid=2001,
            name="game.exe",
            exe_path="C:\\Games\\game.exe",
            category=ProcessCategory.GAME,
            connections_count=1,
            is_limited=False,
            limit_summary="正常",
            sort_priority=3,
            is_protected=False
        )
        self.game_fam = ProcessFamily(
            family_id="game",
            display_name="Game",
            category=ProcessCategory.GAME,
            children=[self.game_item],
            is_protected=False
        )

        self.families = [self.normal_fam, self.sys_fam, self.game_fam]
        self.tree.update_data(self.families)

    def test_select_all_skips_protected_processes(self):
        """测试：全选操作时，受保护的系统进程绝不应被选中"""
        self.tree.select_all(True)
        selected = self.tree.get_selected_targets()
        names = [name.lower() for name, _ in selected]
        
        self.assertIn("normal_app.exe", names)
        self.assertIn("game.exe", names)
        self.assertNotIn("svchost.exe", names)

    def test_invert_selection_skips_protected_processes(self):
        """测试：反选操作时，受保护的系统进程依然保持未选中"""
        self.tree.invert_selection()
        selected = self.tree.get_selected_targets()
        names = [name.lower() for name, _ in selected]
        
        self.assertNotIn("svchost.exe", names)

    def test_filtered_select_all_only_affects_displayed(self):
        """测试：在特定筛选视图下全选，仅选中该筛选可见项，不影响隐藏项"""
        # 仅筛选下载器
        self.tree.apply_filter("", "DOWNLOADER")
        self.assertEqual(len(self.tree.displayed_families), 1)
        self.assertEqual(self.tree.displayed_families[0].family_id, "normal_app")

        self.tree.select_all(True)
        selected = self.tree.get_selected_targets()
        names = [name.lower() for name, _ in selected]

        self.assertIn("normal_app.exe", names)
        self.assertNotIn("game.exe", names)
        self.assertNotIn("svchost.exe", names)


if __name__ == "__main__":
    unittest.main()
