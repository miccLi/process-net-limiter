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

    def test_single_child_selection_does_not_select_siblings(self):
        """测试：多子项家族中仅勾选一个子进程时，绝不连带选中其兄弟进程"""
        child1 = ProcessItem(
            pid=3001, name="steam.exe", exe_path="C:\\Steam\\steam.exe",
            category=ProcessCategory.GAME, connections_count=1,
            is_limited=False, limit_summary="正常", sort_priority=3, is_protected=False
        )
        child2 = ProcessItem(
            pid=3002, name="steamwebhelper.exe", exe_path="C:\\Steam\\bin\\steamwebhelper.exe",
            category=ProcessCategory.GAME, connections_count=3,
            is_limited=False, limit_summary="正常", sort_priority=3, is_protected=False
        )
        steam_fam = ProcessFamily(
            family_id="steam", display_name="Steam",
            category=ProcessCategory.GAME, children=[child1, child2], is_protected=False
        )

        self.tree.update_data([steam_fam])
        self.assertEqual(len(self.tree.displayed_families), 1)

        # 模拟仅勾选 child2 (steamwebhelper.exe)
        steam_item = self.tree.topLevelItem(0)
        self.assertEqual(steam_item.childCount(), 2)
        child2_item = steam_item.child(1)

        # 获取 child2 的 checkbox
        from PyQt5.QtWidgets import QCheckBox
        from PyQt5.QtCore import Qt
        cb2 = self.tree.itemWidget(child2_item, 0).findChild(QCheckBox)
        cb2.setChecked(True)

        selected = self.tree.get_selected_targets()
        names = [name.lower() for name, _ in selected]

        self.assertIn("steamwebhelper.exe", names)
        self.assertNotIn("steam.exe", names)
        self.assertEqual(len(selected), 1)

        # 验证父家族复选框处于 PartiallyChecked (半选) 状态
        fam_cb = self.tree.itemWidget(steam_item, 0).findChild(QCheckBox)
        self.assertEqual(fam_cb.checkState(), Qt.PartiallyChecked)

        # 再次勾选 child1，父家族应变为 Checked
        child1_item = steam_item.child(0)
        cb1 = self.tree.itemWidget(child1_item, 0).findChild(QCheckBox)
        cb1.setChecked(True)
        self.assertEqual(fam_cb.checkState(), Qt.Checked)
        self.assertEqual(len(self.tree.get_selected_targets()), 2)

        # 取消勾选 child1 和 child2，父家族应变为 Unchecked
        cb1.setChecked(False)
        cb2.setChecked(False)
        self.assertEqual(fam_cb.checkState(), Qt.Unchecked)
        self.assertEqual(len(self.tree.get_selected_targets()), 0)

    def test_update_data_preserves_single_child_selection(self):
        """测试：update_data 刷新时保持单个子进程勾选，不反向感染兄弟进程"""
        child1 = ProcessItem(
            pid=4001, name="parent.exe", exe_path="C:\\App\\parent.exe",
            category=ProcessCategory.DOWNLOADER, connections_count=1,
            is_limited=False, limit_summary="正常", sort_priority=1, is_protected=False
        )
        child2 = ProcessItem(
            pid=4002, name="worker.exe", exe_path="C:\\App\\worker.exe",
            category=ProcessCategory.DOWNLOADER, connections_count=2,
            is_limited=False, limit_summary="正常", sort_priority=1, is_protected=False
        )
        fam = ProcessFamily(
            family_id="multi_app", display_name="Multi App",
            category=ProcessCategory.DOWNLOADER, children=[child1, child2], is_protected=False
        )
        self.tree.update_data([fam])

        fam_item = self.tree.topLevelItem(0)
        from PyQt5.QtWidgets import QCheckBox
        cb_worker = self.tree.itemWidget(fam_item.child(1), 0).findChild(QCheckBox)
        cb_worker.setChecked(True)

        self.assertEqual(len(self.tree.get_selected_targets()), 1)

        # 模拟后台定时扫描刷新，传入全新的 ProcessFamily 实例
        new_child1 = ProcessItem(
            pid=4001, name="parent.exe", exe_path="C:\\App\\parent.exe",
            category=ProcessCategory.DOWNLOADER, connections_count=1,
            is_limited=False, limit_summary="正常", sort_priority=1, is_protected=False
        )
        new_child2 = ProcessItem(
            pid=4002, name="worker.exe", exe_path="C:\\App\\worker.exe",
            category=ProcessCategory.DOWNLOADER, connections_count=2,
            is_limited=False, limit_summary="正常", sort_priority=1, is_protected=False
        )
        new_fam = ProcessFamily(
            family_id="multi_app", display_name="Multi App",
            category=ProcessCategory.DOWNLOADER, children=[new_child1, new_child2], is_protected=False
        )
        self.tree.update_data([new_fam])

        selected = self.tree.get_selected_targets()
        names = [name.lower() for name, _ in selected]
        self.assertIn("worker.exe", names)
        self.assertNotIn("parent.exe", names)

    def test_filter_browser_social_and_limited(self):
        """测试：支持 BROWSER_SOCIAL 与 LIMITED 分类过滤"""
        browser_item = ProcessItem(
            pid=5001, name="chrome.exe", exe_path="C:\\Chrome\\chrome.exe",
            category=ProcessCategory.BROWSER_SOCIAL, connections_count=5,
            is_limited=False, limit_summary="正常", sort_priority=4, is_protected=False
        )
        browser_fam = ProcessFamily(
            family_id="chrome", display_name="Chrome",
            category=ProcessCategory.BROWSER_SOCIAL, children=[browser_item], is_protected=False
        )

        limited_item = ProcessItem(
            pid=6001, name="throttled.exe", exe_path="C:\\Apps\\throttled.exe",
            category=ProcessCategory.DOWNLOADER, connections_count=1,
            is_limited=True, limit_summary="100 KB/s", sort_priority=1, is_protected=False
        )
        limited_fam = ProcessFamily(
            family_id="throttled", display_name="Throttled",
            category=ProcessCategory.DOWNLOADER, children=[limited_item], is_protected=False,
            is_limited=True
        )

        self.tree.update_data([browser_fam, limited_fam])

        # 过滤 BROWSER_SOCIAL
        self.tree.apply_filter("", "BROWSER_SOCIAL")
        self.assertEqual(len(self.tree.displayed_families), 1)
        self.assertEqual(self.tree.displayed_families[0].family_id, "chrome")

        # 过滤 LIMITED
        self.tree.apply_filter("", "LIMITED")
        self.assertEqual(len(self.tree.displayed_families), 1)
        self.assertEqual(self.tree.displayed_families[0].family_id, "throttled")


if __name__ == "__main__":
    unittest.main()

