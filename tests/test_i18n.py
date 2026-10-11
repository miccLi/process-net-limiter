# -*- coding: utf-8 -*-
import unittest
from core.i18n import i18n, t, TRANSLATIONS
from core.speed_utils import format_policy_summary, format_speed_display


class TestI18n(unittest.TestCase):
    def setUp(self):
        self.original_lang = i18n.current_lang

    def tearDown(self):
        i18n.set_language(self.original_lang)

    def test_translation_keys_parity(self):
        """测试：中文与英文词条键集完全一致，杜绝漏译"""
        zh_keys = set(TRANSLATIONS["zh_CN"].keys())
        en_keys = set(TRANSLATIONS["en_US"].keys())
        missing_in_en = zh_keys - en_keys
        missing_in_zh = en_keys - zh_keys
        self.assertEqual(missing_in_en, set(), f"英文缺少翻译键: {missing_in_en}")
        self.assertEqual(missing_in_zh, set(), f"中文缺少翻译键: {missing_in_zh}")

    def test_language_switch(self):
        """测试：动态切换语言与 t() 格式化输出"""
        i18n.set_language("zh_CN")
        self.assertEqual(t("app_title"), "进程网络限制器")
        self.assertEqual(t("selected_summary", count=3), "已选择 3 个程序/家族")

        i18n.set_language("en_US")
        self.assertEqual(t("app_title"), "Process Net Limiter")
        self.assertEqual(t("selected_summary", count=3), "Selected 3 program(s) / family(ies)")

    def test_bilingual_speed_utils(self):
        """测试：speed_utils 在中英双语环境下的自适应格式化"""
        # 中文模式
        i18n.set_language("zh_CN")
        self.assertEqual(format_speed_display(0), "不限")
        self.assertEqual(format_policy_summary(True), "⛔ 完全断网")
        self.assertEqual(format_policy_summary(False, 8192, 819200), "上: 1 KB/s | 下: 100 KB/s")

        # 英文模式
        i18n.set_language("en_US")
        self.assertEqual(format_speed_display(0), "Unlimited")
        self.assertEqual(format_policy_summary(True), "⛔ Blocked")
        self.assertEqual(format_policy_summary(False, 8192, 819200), "Up: 1 KB/s | Down: 100 KB/s")


if __name__ == "__main__":
    unittest.main()
